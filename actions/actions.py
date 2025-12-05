from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.forms import FormValidationAction
import re
from datetime import datetime

# Class to validate all form slots in separate methods
class ValidateBookingForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_booking_form"

    # --- NAME ---
    def validate_name(self, slot_value, dispatcher, tracker, domain):
        if len(slot_value.split()) >= 1:
            return {"name": slot_value}
        dispatcher.utter_message(text="That doesn't look like a valid name. Please provide a full name.")
        return {"name": None}

    # --- DATE FORMAT ---
    def valid_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except:
            return False

    def validate_checkin(self, slot_value, dispatcher, tracker, domain):
        if self.valid_date(slot_value):
            return {"checkin": slot_value}
        dispatcher.utter_message(text="Please enter a valid check-in date in format YYYY-MM-DD.")
        return {"checkin": None}

    def validate_checkout(self, slot_value, dispatcher, tracker, domain):
      if self.valid_date(slot_value):
        checkin = tracker.get_slot("checkin")
        checkout_date = datetime.strptime(slot_value, "%Y-%m-%d")
        if checkin:
            checkin_date = datetime.strptime(checkin, "%Y-%m-%d")
            if checkout_date <= checkin_date:
                dispatcher.utter_message(text="Checkout must be after check-in.")
                return {"checkout": None}
            return {"checkout": slot_value}
        return {"checkout": slot_value}
      dispatcher.utter_message(text="Please enter checkout in YYYY-MM-DD format.")
      return {"checkout": None}

    # --- GUESTS ---
    def validate_guests(self, slot_value, dispatcher, tracker, domain):
        if slot_value.isdigit() and int(slot_value) > 0:
            return {"guests": slot_value}
        dispatcher.utter_message(text="Please provide a valid number of guests.")
        return {"guests": None}

    # --- ROOM TYPE ---
    def validate_room_type(self, slot_value, dispatcher, tracker, domain):
        allowed = ["single", "double", "suite"]
        if any(a in slot_value.lower() for a in allowed):
            return {"room_type": slot_value}
        dispatcher.utter_message(text="Room types available: single, double, suite.")
        return {"room_type": None}

    # --- BREAKFAST ---
    def validate_breakfast(self, slot_value, dispatcher, tracker, domain):
        if slot_value.lower() in ["yes", "no"]:
            return {"breakfast": slot_value}
        dispatcher.utter_message(text="Please answer yes or no.")
        return {"breakfast": None}

    # --- PAYMENT ---
    def validate_payment(self, slot_value, dispatcher, tracker, domain):
        slot_value = slot_value.lower()
        if "credit" in slot_value:
           return {"payment": "credit card"}
        if "paypal" in slot_value:
           return {"payment": "paypal"}
        dispatcher.utter_message(text="Payment options: credit card or PayPal.")
        return {"payment": None}

    # --- REFUND ---
    def validate_refund(self, slot_value, dispatcher, tracker, domain):
        allowed = ["refundable", "nonrefundable", "non-refundable"]
        if any(a in slot_value.lower() for a in allowed):
            return {"refund": slot_value}
        dispatcher.utter_message(text="Please choose refundable or non-refundable.")
        return {"refund": None}


class ActionSubmitBooking(Action):

    def name(self) -> Text:
        return "action_submit_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Retrieve the guest name slot
        guest_name = tracker.get_slot("name")

        # Confirmation message using the guest's name
        if guest_name:
            dispatcher.utter_message(
                text=f"Thank you {guest_name}, your booking has been confirmed! 🎉"
            )
        else:
            dispatcher.utter_message(
                text="Your booking has been confirmed! 🎉"
            )

        # Reset all booking slots
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

class ActionCancelBooking(Action):

    def name(self) -> Text:
        return "action_cancel_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Your booking has been cancelled. All details have been cleared.")

        # Reset all booking slots
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