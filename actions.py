from typing import Any, Text, Dict, List, Optional
from datetime import datetime

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict


# =========================================================
# CONSTANTS
# =========================================================

DATE_FORMAT = "%Y-%m-%d"
MAX_GUESTS = 4

ROOM_CAPACITY = {
    "single": 1,
    "double": 2,
    "triple": 3,
    "suite": 4,
}

YES_VALUES = {"yes", "y", "true"}
NO_VALUES = {"no", "n", "false"}


def normalize_text(value: Optional[Text]) -> Optional[Text]:
    return value.strip().lower() if value else None


def interrupt_if_cancelled(
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
) -> Optional[Dict[Text, Any]]:
    """Cancel booking if user says stop or deny."""
    intent = tracker.latest_message.get("intent", {}).get("name")

    if intent in {"stop", "deny"}:
        dispatcher.utter_message(
            text="Okay, I’ve cancelled the booking. If you want to start again, just let me know."
        )
        return {
            "requested_slot": None,
            "active_loop": None,
            "booking_ready": None,
            "name": None,
            "checkin": None,
            "checkout": None,
            "guests": None,
            "room_type": None,
            "breakfast": None,
            "payment": None,
            "refund": None,
        }

    return None


def unclear_value(dispatcher: CollectingDispatcher):
    dispatcher.utter_message(
        text="I’m not sure I understood that. Could you please repeat your answer?"
    )

# =========================================================
# Sgtart booking by setting the initial values for required slots
# =========================================================

class ActionStartBooking(Action):
    def name(self) -> Text:
        return "action_start_booking"

    def run(self, dispatcher, tracker, domain):
        return [
            SlotSet("booking_active", True),
            SlotSet("booking_ready", None),
            SlotSet("requested_slot", "name"),
        ]


# =========================================================
# FORM VALIDATION
# =========================================================

class ValidateBookingForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_booking_form"

    # ---------- NAME ----------
    def validate_name(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"name": None}

        name = value.strip()
        dispatcher.utter_message(f"Great, I have the main guest name as {name}.")
        return {"name": name}

    # ---------- CHECK-IN ----------
    def validate_checkin(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"checkin": None}

        try:
            date = datetime.strptime(value, DATE_FORMAT).date()
            if date <= datetime.today().date():
                dispatcher.utter_message("Checkin must be a future date.")
                return {"checkin": None}

            dispatcher.utter_message(f"Checkin date set to {value}.")
            return {"checkin": value}

        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format for the date.")
            return {"checkin": None}

    # ---------- CHECK-OUT ----------
    def validate_checkout(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"checkout": None}

        try:
            checkout = datetime.strptime(value, DATE_FORMAT).date()
            checkin = tracker.get_slot("checkin")

            if checkin:
                checkin_date = datetime.strptime(checkin, DATE_FORMAT).date()
                if checkout <= checkin_date:
                    dispatcher.utter_message(
                        "Checkout must be after the checkin date."
                    )
                    return {"checkout": None}

            dispatcher.utter_message(f"Check-out date set to {value}.")
            return {"checkout": value}

        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkout": None}

    # ---------- GUESTS ----------
    def validate_guests(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"guests": None}

        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                dispatcher.utter_message(
                    f"Got it — booking for {guests} guest(s)."
                )
                return {"guests": str(guests)}
        except Exception:
            pass

        dispatcher.utter_message("Please enter a number between 1 and 4.")
        return {"guests": None}

    # ---------- ROOM TYPE ----------
    def validate_room_type(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"room_type": None}

        room_type = normalize_text(value)
        guests = tracker.get_slot("guests")

        if not guests:
            dispatcher.utter_message("Let’s confirm the number of guests first.")
            return {"room_type": None, "requested_slot": "guests"}

        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message(
                "Available room types are single, double, triple, or suite."
            )
            return {"room_type": None}

        if int(guests) > ROOM_CAPACITY[room_type]:
            dispatcher.utter_message(
                f"A {room_type} room can host up to {ROOM_CAPACITY[room_type]} guest(s)."
            )
            return {"room_type": None}

        dispatcher.utter_message(f"{room_type.capitalize()} room selected.")
        return {"room_type": room_type}

    # ---------- BREAKFAST ----------
    def validate_breakfast(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

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

    # ---------- PAYMENT ----------
    def validate_payment(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"payment": None}

        norm = normalize_text(value)

        if "credit" in norm:
            dispatcher.utter_message("Payment method is set to credit card.")
            return {"payment": "credit card"}

        if "cash" in norm:
            dispatcher.utter_message("Payment method is set to cash.")
            return {"payment": "cash"}

        dispatcher.utter_message("Please choose credit card or cash.")
        return {"payment": None}

    # ---------- REFUND ----------
    def validate_refund(self, value, dispatcher, tracker, domain):

        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
            return interrupt

        if not value:
            unclear_value(dispatcher)
            return {"refund": None}

        norm = normalize_text(value)

        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            dispatcher.utter_message(f"Refund policy set to {norm}.")
            return {"refund": norm}

        dispatcher.utter_message("Please choose refundable or non-refundable.")
        return {"refund": None}


# =========================================================
# SUBMIT BOOKING
# =========================================================

class ActionSubmitBooking(Action):

    def name(self) -> Text:
        return "action_submit_booking"

    def run(self, dispatcher, tracker, domain):

        required = domain["forms"]["booking_form"]["required_slots"]

        if any(tracker.get_slot(s) is None for s in required):
            return []

        dispatcher.utter_message(template="utter_summary")

        return [
            SlotSet("booking_ready", True),
            SlotSet("booking_active", False),
        ]


# =========================================================
# CONFIRM BOOKING
# =========================================================

class ActionSubmitBookingConfirmed(Action):

    def name(self) -> Text:
        return "action_submit_booking_confirmed"

    def run(self, dispatcher, tracker, domain):

        if not tracker.get_slot("booking_ready"):
            dispatcher.utter_message("There is no booking to confirm.")
            return []

        name = tracker.get_slot("name")

        dispatcher.utter_message(
            f"✅ Thank you {name}, your booking is confirmed!"
            if name else
            "✅ Your booking is confirmed!"
        )

        return [
            SlotSet("booking_ready", None),
            SlotSet("booking_active", None),
            SlotSet("name", None),
            SlotSet("checkin", None),
            SlotSet("checkout", None),
            SlotSet("guests", None),
            SlotSet("room_type", None),
            SlotSet("breakfast", None),
            SlotSet("payment", None),
            SlotSet("refund", None),
        ]


# =========================================================
# CANCEL BOOKING
# =========================================================

class ActionCancelBooking(Action):

    def name(self) -> Text:
        return "action_cancel_booking"

    def run(self, dispatcher, tracker, domain):

        dispatcher.utter_message("Your booking has been cancelled.")

        return [
            SlotSet("booking_ready", None),
            SlotSet("booking_active", None),
            SlotSet("name", None),
            SlotSet("checkin", None),
            SlotSet("checkout", None),
            SlotSet("guests", None),
            SlotSet("room_type", None),
            SlotSet("breakfast", None),
            SlotSet("payment", None),
            SlotSet("refund", None),
        ]