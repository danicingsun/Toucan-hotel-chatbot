from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict

from datetime import datetime


# =========================================================
# CONSTANTS & HELPERS
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


def has_active_booking(tracker: Tracker) -> bool:
    """Check whether any booking-related slot is filled."""
    return any(
        tracker.get_slot(slot)
        for slot in [
            "name",
            "checkin",
            "checkout",
            "guests",
            "room_type",
            "breakfast",
            "payment",
            "refund",
        ]
    )


# =========================================================
# FORM VALIDATION
# =========================================================

class ValidateBookingForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_booking_form"

    # -------- GLOBAL INTERRUPTS (cancel / stop) --------
    def validate(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        intent = tracker.latest_message.get("intent", {}).get("name")

        if intent == "stop":
            if not has_active_booking(tracker):
                dispatcher.utter_message(
                    text="There is no active booking to cancel."
                )
                return {"requested_slot": None}

            dispatcher.utter_message(
                text="Your booking has been cancelled. All details were cleared."
            )
            return {
                "requested_slot": None,
                "active_loop": None,
                "name": None,
                "checkin": None,
                "checkout": None,
                "guests": None,
                "room_type": None,
                "breakfast": None,
                "payment": None,
                "refund": None,
            }

        return {}

    # -------- NAME --------
    def validate_name(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        name = value.strip() if value else None
        if name:
            return {"name": name}

        dispatcher.utter_message(text="Please provide a valid name.")
        return {"name": None}

    # -------- CHECK-IN --------
    def validate_checkin(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        try:
            checkin_date = datetime.strptime(value, DATE_FORMAT).date()
            today = datetime.today().date()

            if checkin_date <= today:
                dispatcher.utter_message(
                    text="Check-in must be a future date."
                )
                return {"checkin": None}

            return {"checkin": value}

        except Exception:
            dispatcher.utter_message(
                text="Please enter the check-in date in YYYY-MM-DD format."
            )
            return {"checkin": None}

    # -------- CHECK-OUT --------
    def validate_checkout(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        try:
            checkout_date = datetime.strptime(value, DATE_FORMAT).date()
            checkin_value = tracker.get_slot("checkin")

            if checkin_value:
                checkin_date = datetime.strptime(
                    checkin_value, DATE_FORMAT
                ).date()

                if checkout_date <= checkin_date:
                    dispatcher.utter_message(
                        text="Check-out must be after the check-in date."
                    )
                    return {"checkout": None}

            return {"checkout": value}

        except Exception:
            dispatcher.utter_message(
                text="Please enter the check-out date in YYYY-MM-DD format."
            )
            return {"checkout": None}

    # -------- GUESTS --------
    def validate_guests(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                return {"guests": str(guests)}

        except Exception:
            pass

        dispatcher.utter_message(
            text=(
                "Please enter a valid number of guests (1–4). "
                "Only one room can be booked at a time. "
                "Children over 2 years count as guests."
            )
        )
        return {"guests": None}

    # -------- ROOM TYPE --------
    def validate_room_type(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        room_type = normalize_text(value)
        guests_raw = tracker.get_slot("guests")

        # Validate guests first
        try:
            guests = int(guests_raw)
        except Exception:
            dispatcher.utter_message(
                text="Let's confirm the number of guests first."
            )
            return {
                "room_type": None,
                "guests": None,
                "requested_slot": "guests",
            }

        # Absolute limit safety net
        if guests > MAX_GUESTS:
            dispatcher.utter_message(
                text="We can accommodate up to 4 guests per booking."
            )
            return {
                "room_type": None,
                "guests": None,
                "requested_slot": "guests",
            }

        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message(
                text="Available room types are single, double, triple, or suite."
            )
            return {"room_type": None}

        if guests > ROOM_CAPACITY[room_type]:
            dispatcher.utter_message(
                text=(
                    f"A {room_type} room can host up to "
                    f"{ROOM_CAPACITY[room_type]} guest(s). "
                    "Please choose another room type."
                )
            )
            return {"room_type": None}

        return {"room_type": room_type}

    # -------- BREAKFAST --------
    def validate_breakfast(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        norm = normalize_text(value)

        if norm in YES_VALUES:
            return {"breakfast": "yes"}
        if norm in NO_VALUES:
            return {"breakfast": "no"}

        dispatcher.utter_message(text="Please answer yes or no.")
        return {"breakfast": None}

    # -------- PAYMENT --------
    def validate_payment(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        norm = normalize_text(value)

        if "credit" in norm:
            return {"payment": "credit card"}
        if "cash" in norm:
            return {"payment": "cash"}

        dispatcher.utter_message(
            text="Payment options are credit card or cash."
        )
        return {"payment": None}

    # -------- REFUND --------
    def validate_refund(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:

        norm = normalize_text(value)

        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            return {"refund": norm}

        dispatcher.utter_message(
            text="Please choose refundable or non-refundable."
        )
        return {"refund": None}


# =========================================================
# SUBMIT BOOKING
# =========================================================

class ActionSubmitBooking(Action):

    def name(self) -> Text:
        return "action_submit_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        name = tracker.get_slot("name")

        dispatcher.utter_message(
            text=f"Thank you {name}, your booking has been confirmed! 🎉"
            if name
            else "Your booking has been confirmed! 🎉"
        )

        return [SlotSet(slot, None) for slot in [
            "name",
            "checkin",
            "checkout",
            "guests",
            "room_type",
            "breakfast",
            "payment",
            "refund",
        ]]


# =========================================================
# CANCEL BOOKING
# =========================================================

class ActionCancelBooking(Action):

    def name(self) -> Text:
        return "action_cancel_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        has_booking = any(
            tracker.get_slot(slot)
            for slot in [
                "name",
                "checkin",
                "checkout",
                "guests",
                "room_type",
            ]
        )

        if not has_booking:
            dispatcher.utter_message(
                text="You don’t have an active booking to cancel."
            )
            return []

        dispatcher.utter_message(
            text="Your booking has been cancelled. All details were cleared."
        )

        return [
            SlotSet("name", None),
            SlotSet("checkin", None),
            SlotSet("checkout", None),
            SlotSet("guests", None),
            SlotSet("room_type", None),
            SlotSet("breakfast", None),
            SlotSet("payment", None),
            SlotSet("refund", None),
        ]