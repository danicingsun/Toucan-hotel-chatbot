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

#Helper function to interrupt the form if user start chitchat or asks a question
def interrupt_if_cancelled(
    dispatcher: CollectingDispatcher,
    tracker: Tracker,
) -> Optional[Dict[Text, Any]]:

    intent = tracker.latest_message.get("intent", {}).get("name")

    if intent == "stop":
        dispatcher.utter_message(
            text="I am not sure I understand you. I will cancel the booking and if that was not your intent, I can help you start over."
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

    return None

#Function to check if all slots are filled yet
def all_required_slots_filled(
    tracker: Tracker,
    domain: DomainDict,
    form_name: Text = "booking_form",
) -> bool:
    required_slots = domain["forms"][form_name]["required_slots"]

    return all(tracker.get_slot(slot) is not None for slot in required_slots)


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
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt

        #Check if user replied with a string
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
	#Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt

	#Continue with validation checks
        try:
            checkin_date = datetime.strptime(value, DATE_FORMAT).date()
            today = datetime.today().date()
	    
            #Make sure checkin is in the future
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks
        try:
            checkout_date = datetime.strptime(value, DATE_FORMAT).date()
            checkin_value = tracker.get_slot("checkin")

            #Make sure checkout date is after checkin date
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks
        #Check the number of guests does not exceed the maximum, which is currently 4
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
                "Children over 2 years count as guests. Children under 2 years are welcome to stay in a cot that can be picked up at reception at arrival time."
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks
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

        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message(
                text="Available room types are single, double, triple, or suite."
            )
            return {"room_type": None}
        
        #Only allow room types that will fit all the guests in the booking
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks - only yes or no are accepted
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks - only allow cash or credit card
        norm = normalize_text(value)

        if "credit" in norm:
            dispatcher.utter_message(
                text="We will expect payment by credit card at arrival time"
            )
            return {"payment": "credit card"}
        if "cash" in norm:
            dispatcher.utter_message(
                text="We will expect cash payment at arrival time"
            )
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
	
        #Interrupt the form if user starts chitchat
        interrupt = interrupt_if_cancelled(dispatcher, tracker)
        if interrupt:
        	return interrupt
	
        #Continue with validation checks - only refundable or non-refundable are accepted
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
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:

        required_slots = domain["forms"]["booking_form"]["required_slots"]

        missing_slots = [
            slot for slot in required_slots
            if not tracker.get_slot(slot)
        ]

        # Safety net (rare but correct)
        if missing_slots:
            dispatcher.utter_message(
                text="Your booking is not complete yet. Let's finish it first."
            )
            return []

        # ONLY show summary and ask for confirmation
        dispatcher.utter_message(template="utter_summary")
        return []

class ActionSubmitBookingConfirmed(Action):

    def name(self) -> Text:
        return "action_submit_booking_confirmed"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:

        name = tracker.get_slot("name")

        # Final confirmation message
        dispatcher.utter_message(
            text=(
                f"Thank you {name}, your booking has been confirmed! 🎉 "
                "We look forward to welcoming you. "
                "If you need anything else, just let me know."
            )
            if name else
            "Your booking has been confirmed! 🎉 "
            "We look forward to welcoming you. "
            "If you need anything else, just let me know."
        )

        # Clear all booking-related slots
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
            text="Your booking has been cancelled. All details were cleared. Could I help you with anything else today?"
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