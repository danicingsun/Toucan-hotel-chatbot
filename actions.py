from typing import Text, Optional, Dict, Any
from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import SlotSet, ActiveLoop

# =========================
# CONSTANTS
# =========================
DATE_FORMAT = "%Y-%m-%d"
MAX_GUESTS = 4
ROOM_CAPACITY = {"single": 1, "double": 2, "triple": 3, "suite": 4}
YES_VALUES = {"yes", "y", "true"}
NO_VALUES = {"no", "n", "false"}


# =========================
# UTILITY FUNCTIONS
# =========================
def normalize_text(value: Optional[Text]):
    return value.strip().lower() if value else None


def unclear_value(dispatcher: CollectingDispatcher):
    dispatcher.utter_message(
        text="I’m not sure I understood that. Could you please repeat your answer?"
    )


def form_is_active(tracker: Tracker):
    return tracker.active_loop is not None


# =========================
# FORM VALIDATION
# =========================
class ValidateBookingForm(FormValidationAction):

    def name(self):
        return "validate_booking_form"

    def _is_cancel(self, tracker: Tracker):
        return tracker.latest_message.intent.get("name") == "stop"

    # -------------------------
    # Name
    # -------------------------
    def validate_name(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

        if not value or len(value.split()) > 4 or any(
            word in value.lower() for word in ["book", "start", "cancel", "stop", "booking", "deny", "room", "please"]
        ):
            unclear_value(dispatcher)
            return {"name": None}

        dispatcher.utter_message(f"Great, I have the main guest name as {value.strip()}.")
        return {"name": value.strip()}

    # -------------------------
    # Check-in
    # -------------------------
    def validate_checkin(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

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
        except ValueError:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkin": None}

    # -------------------------
    # Check-out
    # -------------------------
    def validate_checkout(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

        if not value:
            unclear_value(dispatcher)
            return {"checkout": None}

        try:
            checkout_date = datetime.strptime(value, DATE_FORMAT).date()
            checkin_value = tracker.get_slot("checkin")
            if checkin_value:
                checkin_date = datetime.strptime(checkin_value, DATE_FORMAT).date()
                if checkout_date <= checkin_date:
                    dispatcher.utter_message("Checkout must be after the check-in date.")
                    return {"checkout": None}
            dispatcher.utter_message(f"Check-out date set to {value}.")
            return {"checkout": value}
        except ValueError:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkout": None}

    # -------------------------
    # Guests
    # -------------------------
    def validate_guests(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

        if not value:
            unclear_value(dispatcher)
            return {"guests": None}

        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                dispatcher.utter_message(f"Got it — booking for {guests} guest(s).")
                return {"guests": str(guests)}
        except ValueError:
            pass

        dispatcher.utter_message(f"Please enter a number between 1 and {MAX_GUESTS}.")
        return {"guests": None}

    # -------------------------
    # Room type
    # -------------------------
    def validate_room_type(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

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

    # -------------------------
    # Breakfast
    # -------------------------
    def validate_breakfast(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

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

    # -------------------------
    # Payment
    # -------------------------
    def validate_payment(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

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

    # -------------------------
    # Refund
    # -------------------------
    def validate_refund(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        if not form_is_active(tracker) or self._is_cancel(tracker):
            return {"requested_slot": None}

        if not value:
            unclear_value(dispatcher)
            return {"refund": None}

        norm = normalize_text(value)
        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            dispatcher.utter_message(f"Refund policy set to {norm}.")
            return {"refund": norm}

        dispatcher.utter_message("Please choose refundable or non-refundable.")
        return {"refund": None}


# =========================
# FORM SUBMISSION
# =========================
class ActionSubmitBooking(Action):
    def name(self):
        return "action_submit_booking"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict):
        dispatcher.utter_message(template="utter_summary")
        return [SlotSet("booking_ready", True)]


class ActionSubmitBookingConfirmed(Action):
    def name(self):
        return "action_submit_booking_confirmed"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict):
        name = tracker.get_slot("name")
        dispatcher.utter_message(
            f"✅ Thank you {name}, your booking is confirmed!" if name else "✅ Your booking is confirmed!"
        )

        slots_to_clear = [
            "booking_ready", "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "requested_slot"
        ]
        return [SlotSet(slot, None) for slot in slots_to_clear] + [ActiveLoop(None)]


# =========================
# CANCEL BOOKING
# =========================
class ActionCancelBooking(Action):
    def name(self):
        return "action_cancel_booking"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict):
        dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")

        slots_to_clear = [
            "booking_ready", "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "requested_slot"
        ]
        return [SlotSet(slot, None) for slot in slots_to_clear] + [ActiveLoop(None)]