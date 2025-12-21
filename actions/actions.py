from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.forms import FormValidationAction

from datetime import datetime


# =========================================================
# FORM VALIDATION
# =========================================================

class ValidateBookingForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_booking_form"

    # -------- NAME --------
    def validate_name(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if value and len(value.strip()) > 0:
            return {"name": value.strip()}
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
            checkin_date = datetime.strptime(value, "%Y-%m-%d").date()
            today = datetime.today().date()

            if checkin_date <= today:
                dispatcher.utter_message(text="Check-in must be a future date.")
                return {"checkin": None}

            return {"checkin": value}
        except ValueError:
            dispatcher.utter_message(text="Enter check-in date as YYYY-MM-DD.")
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
            checkout_date = datetime.strptime(value, "%Y-%m-%d").date()
            checkin = tracker.get_slot("checkin")

            if checkin:
                checkin_date = datetime.strptime(checkin, "%Y-%m-%d").date()
                if checkout_date <= checkin_date:
                    dispatcher.utter_message(
                        text="Checkout must be after the check-in date."
                    )
                    return {"checkout": None}

            return {"checkout": value}
        except ValueError:
            dispatcher.utter_message(text="Enter checkout date as YYYY-MM-DD.")
            return {"checkout": None}

    # -------- GUESTS --------
    def validate_guests(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if value.isdigit() and int(value) > 0:
            return {"guests": value}
        dispatcher.utter_message(text="Please enter a valid number of guests.")
        return {"guests": None}

    # -------- ROOM TYPE --------
    def validate_room_type(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        allowed = ["single", "double", "suite"]
        norm = value.lower()
        if norm in allowed:
            return {"room_type": norm}
        dispatcher.utter_message(
            text="Room types available: single, double, suite."
        )
        return {"room_type": None}

    # -------- BREAKFAST --------
    def validate_breakfast(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not value:
            return {"breakfast": None}

        norm = value.strip().lower()
        if norm in ["yes", "y", "true"]:
            return {"breakfast": "yes"}
        if norm in ["no", "n", "false"]:
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
        norm = value.lower()
        if "credit" in norm:
            return {"payment": "credit card"}
        if "paypal" in norm:
            return {"payment": "paypal"}
        dispatcher.utter_message(
            text="Payment options are credit card or PayPal."
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
        norm = value.lower()
        if norm in ["refundable", "non-refundable", "nonrefundable"]:
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

        if name:
            dispatcher.utter_message(
                text=f"Thank you {name}, your booking has been confirmed! 🎉"
            )
        else:
            dispatcher.utter_message(
                text="Your booking has been confirmed! 🎉"
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