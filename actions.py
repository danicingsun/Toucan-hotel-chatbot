from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import SlotSet, ActiveLoop

# ============================================================
# CONSTANTS
# ============================================================
DATE_FORMAT = "%Y-%m-%d"
MAX_GUESTS = 4
ROOM_CAPACITY = {"single": 1, "double": 2, "triple": 3, "suite": 4}
YES_VALUES = {"yes", "y", "true"}
NO_VALUES = {"no", "n", "false"}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def normalize_text(value):
    """Convert a string to lowercase and strip spaces."""
    return value.strip().lower() if value else None


def unclear_value(dispatcher):
    """Send a generic message when input is unclear."""
    dispatcher.utter_message(
        text="I’m not sure I understood that. Could you please repeat your answer?"
    )


def form_is_active(tracker):
    """Check if a form is currently active."""
    return tracker.active_loop is not None


# ============================================================
# BASE VALIDATION CLASS
# ============================================================
class ValidateBookingForm(FormValidationAction):
    """Validation class for the booking form."""

    def name(self):
        return "validate_booking_form"

    # -------------------------
    # Helper functions
    # -------------------------
    def _is_cancel(self, tracker):
        """Check if the user wants to cancel the booking."""
        return tracker.latest_message.get("intent", {}).get("name") == "stop"

    def _validate_slot(self, tracker, dispatcher):
        """
        Common early checks for all slots:
        - If the form is not active, skip validation.
        - If the user wants to cancel, stop the form.
        """
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}
        return None

    # -------------------------
    # Slot validation methods
    # -------------------------
    def validate_name(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value or len(value.split()) > 4 or any(
            word in value.lower()
            for word in ["book", "start", "cancel", "stop", "booking", "deny", "room", "please"]
        ):
            unclear_value(dispatcher)
            return {"name": None}

        dispatcher.utter_message(f"Great, I have the main guest name as {value.strip()}.")
        return {"name": value.strip()}

    def validate_checkin(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"checkin": None}

        try:
            date = datetime.strptime(value, DATE_FORMAT).date()
            if date <= datetime.today().date():
                dispatcher.utter_message("Check-in must be a future date.")
                return {"checkin": None}
            dispatcher.utter_message(f"Check-in date set to {value}.")
            return {"checkin": value}
        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkin": None}

    def validate_checkout(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"checkout": None}

        try:
            checkout = datetime.strptime(value, DATE_FORMAT).date()
            checkin = tracker.get_slot("checkin")
            if checkin:
                checkin_date = datetime.strptime(checkin, DATE_FORMAT).date()
                if checkout <= checkin_date:
                    dispatcher.utter_message("Checkout must be after the check-in date.")
                    return {"checkout": None}
            dispatcher.utter_message(f"Check-out date set to {value}.")
            return {"checkout": value}
        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkout": None}

    def validate_guests(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"guests": None}

        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                dispatcher.utter_message(f"Got it — booking for {guests} guest(s).")
                return {"guests": str(guests)}
        except Exception:
            pass

        dispatcher.utter_message(f"Please enter a number between 1 and {MAX_GUESTS}.")
        return {"guests": None}

    def validate_room_type(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"room_type": None}

        room_type = normalize_text(value)
        guests = tracker.get_slot("guests")

        if not guests:
            dispatcher.utter_message("Let’s confirm the number of guests first.")
            return {"room_type": None}

        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message("Available room types: single, double, triple, suite.")
            return {"room_type": None}

        if int(guests) > ROOM_CAPACITY[room_type]:
            dispatcher.utter_message(
                f"A {room_type} room can host up to {ROOM_CAPACITY[room_type]} guest(s)."
            )
            return {"room_type": None}

        dispatcher.utter_message(f"{room_type.capitalize()} room selected.")
        return {"room_type": room_type}

    def validate_breakfast(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"breakfast": None}

        norm = normalize_text(value)
        if norm in YES_VALUES:
            dispatcher.utter_message("Breakfast will be included.")
            return {"breakfast": "yes"}
        if norm in NO_VALUES:
            dispatcher.utter_message("No breakfast will be included.")
            return {"breakfast": "no"}

        dispatcher.utter_message("Please answer yes or no.")
        return {"breakfast": None}

    def validate_payment(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"payment": None}

        norm = normalize_text(value)
        if "credit" in norm:
            dispatcher.utter_message("Payment method set to credit card.")
            return {"payment": "credit card"}
        if "cash" in norm:
            dispatcher.utter_message("Payment method set to cash.")
            return {"payment": "cash"}

        dispatcher.utter_message("Please choose credit card or cash.")
        return {"payment": None}

    def validate_refund(self, value, dispatcher, tracker, domain):
        result = self._validate_slot(tracker, dispatcher)
        if result:
            return result

        if not value:
            unclear_value(dispatcher)
            return {"refund": None}

        norm = normalize_text(value)
        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            dispatcher.utter_message(f"Refund policy set to {norm}.")
            return {"refund": norm}

        dispatcher.utter_message("Please choose refundable or non-refundable.")
        return {"refund": None}


# ============================================================
# FORM SUBMISSION ACTIONS
# ============================================================
class ActionSubmitBooking(Action):
    """Trigger after the form is completed but before confirmation."""

    def name(self):
        return "action_submit_booking"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(template="utter_summary")
        return [SlotSet("booking_ready", True)]


class ActionSubmitBookingConfirmed(Action):
    """Confirm the booking and clear all form slots."""

    def name(self):
        return "action_submit_booking_confirmed"

    def run(self, dispatcher, tracker, domain):
        name = tracker.get_slot("name")
        dispatcher.utter_message(
            f"✅ Thank you {name}, your booking is confirmed!"
            if name else "✅ Your booking is confirmed!"
        )

        return [SlotSet(slot, None) for slot in [
            "booking_ready", "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "requested_slot"
        ]] + [ActiveLoop(None)]


# ============================================================
# CANCEL BOOKING ACTION
# ============================================================
class ActionCancelBooking(Action):
    """Cancel the booking and clear all slots."""

    def name(self):
        return "action_cancel_booking"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")

        return [SlotSet(slot, None) for slot in [
            "booking_ready", "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "requested_slot"
        ]] + [ActiveLoop(None)]