from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, ActiveLoop, FollowupAction
import os 
import smtplib 
import re
import logging
from email.mime.text import MIMEText 
from typing import Any, Dict, Text
from rasa_sdk.types import DomainDict


# ============================================================
# Constants
# ============================================================
DATE_FORMAT = "%Y-%m-%d"
MAX_GUESTS = 4
ROOM_CAPACITY = {"single": 1, "double": 2, "triple": 3, "suite": 4}
YES_VALUES = {"yes", "y", "true"}
NO_VALUES = {"no", "n", "false"}

logger = logging.getLogger(__name__)

# ============================================================
# Utility functions
# ============================================================
def normalize_text(value):
    return value.strip().lower() if value else None

def unclear_value(dispatcher):
    dispatcher.utter_message("I’m not sure I understood that. Could you please repeat your answer?")

# ============================================================
# Form validation
# ============================================================
class ValidateBookingForm(FormValidationAction):
    def name(self) -> str:
        return "validate_booking_form"

    # --------------------------
    # Slot validators
    # --------------------------
    def validate_booking_field(self, value, dispatcher, tracker, domain):
        return {"booking_field": value}

    def validate_name(self, value, dispatcher, tracker, domain): 
        if not value or len(value.split()) > 4 or any(word in value.lower() for word in ["book", "start", "cancel", "stop", "booking", "deny", "room", "please"]):
            unclear_value(dispatcher)
            return {"name": None}
        return {"name": value.strip()}

    def validate_email( 
        self, 
        slot_value: Any, 
        dispatcher: CollectingDispatcher, 
        tracker: Tracker, 
        domain: DomainDict, 
    ) -> Dict[Text, Any]: 

        # Establish correct email pattern
        email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$" 
        
        if re.match(email_pattern, slot_value): return {"email": slot_value} 

        dispatcher.utter_message( text="That doesn’t look like a valid email address. Could you enter it again?" ) 

        return {"email": None}

    # Validate if checkin date is in the correct format and only accept that format
    def validate_checkin(self, value, dispatcher, tracker, domain):
        if not value:
            unclear_value(dispatcher)
            return {"checkin": None}
        try:
            date = datetime.strptime(value, DATE_FORMAT).date()
            if date <= datetime.today().date():
                dispatcher.utter_message("Check-in must be a future date.")
                return {"checkin": None}
            return {"checkin": value}
        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkin": None}
    # Validate if checkout date is in the correct format and only accept that format and also that it is after checkin date
    def validate_checkout(self, value, dispatcher, tracker, domain): 
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
            return {"checkout": value}
        except Exception:
            dispatcher.utter_message("Please use YYYY-MM-DD format.")
            return {"checkout": None}

    # Maximum number of guests allowed is 4, because user can book only one room at a time
    def validate_guests(self, value, dispatcher, tracker, domain):
        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                return {"guests": str(guests)}
        except Exception:
            pass
        dispatcher.utter_message("Please enter a number between 1 and 4.")
        return {"guests": None}

    # Validate room type against number of guests
    def validate_room_type(self, value, dispatcher, tracker, domain):
        room_type = normalize_text(value)
        guests = tracker.get_slot("guests")
        # Make sure number of guests is set
        if not guests:
            dispatcher.utter_message("Let’s confirm the number of guests first.")
            return {"room_type": None}
        # Make sure the selected type of room can accommodate the number of guests
        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message("Available room types: single, double, triple, suite.")
            return {"room_type": None}

        if int(guests) > ROOM_CAPACITY[room_type]:
            dispatcher.utter_message(f"A {room_type} room can host up to {ROOM_CAPACITY[room_type]} guest(s).")
            return {"room_type": None}

        return {"room_type": room_type}

    # Make sure that breakfast is set to yes or no only
    def validate_breakfast(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if norm in YES_VALUES:
            return {"breakfast": "yes"}
        if norm in NO_VALUES:
            return {"breakfast": "no"}
        dispatcher.utter_message("Please answer yes or no.")
        return {"breakfast": None}

    # Make sure payment types are only credit card and cash
    def validate_payment(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if "credit" in norm:
            return {"payment": "credit card"}
        if "cash" in norm:
            return {"payment": "cash"}
        dispatcher.utter_message("Please choose credit card or cash.")
        return {"payment": None}

    # Make sure that refund is set to yes or no only
    def validate_refund(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            return {"refund": norm}
        
        dispatcher.utter_message("Please choose refundable or non-refundable.")
        return {"refund": None}

    # Make sure that confirmation is set to yes or no only
    def validate_confirmation(self, value, dispatcher, tracker, domain): 
        if value == "yes": 
            return {"confirmation": "yes"} 
        if value == "no": 
            return {"confirmation": "no"}
        dispatcher.utter_message("Please confirm with yes or no.") 
        return {"confirmation": None}

# ============================================================
# Cancel booking action: when triggered it resets all slots
# ============================================================
class ActionCancelBooking(Action):
    def name(self):
        return "action_cancel_booking"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")
        slots_to_reset = [
            "name", "email", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment",
            "refund", "confirmation", "booking_field"
        ]

        events = [SlotSet(slot, None) for slot in slots_to_reset]

        events.append(SlotSet("requested_slot", None))
        events.append(ActiveLoop(None))

        return events


# ============================================================
# Confirm booking action: 
# ============================================================
class ActionSubmitBookingConfirmed(Action):
    def name(self):
        return "action_submit_booking_confirmed"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        confirmation = tracker.get_slot("confirmation")

        # If not confirmed, cancel message, reset slots and end loop
        if confirmation != "yes":
            dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")
            return [
                SlotSet("name", None),
                SlotSet("email", None),
                SlotSet("checkin", None),
                SlotSet("checkout", None),
                SlotSet("guests", None),
                SlotSet("room_type", None),
                SlotSet("breakfast", None),
                SlotSet("payment", None),
                SlotSet("refund", None),
                SlotSet("confirmation", None),
                SlotSet("requested_slot", None),
                ActiveLoop(None),
            ]

        # If confirmed print message and send configuration email
        name = tracker.get_slot("name")
        user_email = tracker.get_slot("email")

        dispatcher.utter_message(
            f"✅ Thank you {name}, your booking is confirmed! We look forward to welcoming you at our hotel!"
            if name
            else "✅ Your booking is confirmed! We look forward to welcoming you at our hotel!"
        )

        events = [
            # end the form loop
            SlotSet("requested_slot", None),
            ActiveLoop(None),
        ]

        # Trigger email only if we actually have an email
        if user_email:
            events.append(FollowupAction("action_send_confirmation_email"))
        else:
            dispatcher.utter_message("I don’t have an email address on file, so I can’t send a confirmation email.")
        return events


# ============================================================
# Handle change in booking
# ============================================================
class ActionHandleChange(Action):
    def name(self) -> str:
        return "action_handle_change"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        field = next(tracker.get_latest_entity_values("booking_field"), None)

        if not field:
            dispatcher.utter_message(
                "Sure — what would you like to change? "
                "You can say name, check-in, check-out, guests, room type, breakfast, payment, refund, or email."
            )
            return []

        allowed = {
            "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "email"
        }
        if field not in allowed:
            dispatcher.utter_message("That field cannot be changed.")
            return []

        dispatcher.utter_message(f"Okay, let's update your {field}.")

        events = [SlotSet(field, None), SlotSet("requested_slot", field)]

        if field == "guests":
            events.insert(1, SlotSet("room_type", None))  # dependency reset

        if field == "checkin":
            events.insert(1, SlotSet("checkout", None))

        return events

# ============================================================
# Send confirmation email
# ============================================================
class ActionSendConfirmationEmail(Action): 

    def name(self) -> str: 
        return "action_send_confirmation_email" 

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        # Retrieve secrets from environment variables 
        email_user = os.getenv("EMAIL_USER") 
        email_password = os.getenv("EMAIL_PASSWORD") 

        # Retrieve booking details from slots 
        user_email = tracker.get_slot("email") 
        check_in = tracker.get_slot("checkin") 
        check_out = tracker.get_slot("checkout") 
        room_type = tracker.get_slot("room_type") 
        guests = tracker.get_slot("guests") 
        breakfast = tracker.get_slot("breakfast")
        payment = tracker.get_slot("payment")
        refund = tracker.get_slot("refund")

        # Check if hotel email is provided as server variable
        if not email_user or not email_password:
           dispatcher.utter_message("Email is not configured on the server, but your booking is confirmed.")
           return [
               SlotSet("name", None),
               SlotSet("email", None),
               SlotSet("checkin", None),
               SlotSet("checkout", None),
               SlotSet("guests", None),
               SlotSet("room_type", None),
               SlotSet("breakfast", None),
               SlotSet("payment", None),
               SlotSet("refund", None),
               SlotSet("confirmation", None),
               SlotSet("requested_slot", None),
               ActiveLoop(None),
            ]

        # Build email content 
        body = ( 
            f"Thank you for your reservation!\n\n" 
            f"Here are your booking details:\n" 
            f"- Room type: {room_type}\n" 
            f"- Guests: {guests}\n" 
            f"- Check-in: {check_in}\n" 
            f"- Check-out: {check_out}\n" 
            f"- Breakfast included: {breakfast}\n" 
            f"- Refund policy: {refund}\n" 
            f"- Payment method: {payment}\n\n" 
            f"We look forward to welcoming you at hotel Van Der Valk!" 
         ) 
  
        msg = MIMEText(body)
        msg["Subject"] = "Your Hotel Booking Confirmation" 
        msg["From"] = email_user 
        msg["To"] = user_email 

        try: 
            # Gmail SMTP with SSL 
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:                  
                server.login(email_user, email_password) 
                server.send_message(msg) 

            dispatcher.utter_message("Your confirmation email has been sent.") 
        except Exception as e: 
            dispatcher.utter_message( 
                "I couldn't send the confirmation email, but your booking is saved." 
            ) 
            logger.exception("Email send failed")

        return [
            SlotSet("name", None),
            SlotSet("email", None),
            SlotSet("checkin", None),
            SlotSet("checkout", None),
            SlotSet("guests", None),
            SlotSet("room_type", None),
            SlotSet("breakfast", None),
            SlotSet("payment", None),
            SlotSet("refund", None),
            SlotSet("confirmation", None),
            SlotSet("requested_slot", None),
            ActiveLoop(None),
        ]
