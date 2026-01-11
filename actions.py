from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
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
# UTILITY FUNCTIONS
# ============================================================
def normalize_text(value):
    return value.strip().lower() if value else None

def unclear_value(dispatcher):
    dispatcher.utter_message("I’m not sure I understood that. Could you please repeat your answer?")

# ============================================================
# FORM VALIDATION
# ============================================================
class ValidateBookingForm(FormValidationAction):
    def name(self) -> str:
        return "validate_booking_form"

    # Generic validate function to check for intent first
    def validate(self, dispatcher, tracker, domain):
        intent = tracker.latest_message.get("intent", {}).get("name")

        # Only short-circuit when changing booking
        if intent == "change_booking":
            return {}

        return super().validate(dispatcher, tracker, domain)


    # --------------------------
    # Slot validators
    # --------------------------
    def validate_name(self, value, dispatcher, tracker, domain):
        if not value or len(value.split()) > 4 or any(word in value.lower() for word in ["book", "start", "cancel", "stop", "booking", "deny", "room", "please"]):
            unclear_value(dispatcher)
            return {"name": None}
        return {"name": value.strip()}

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

    def validate_guests(self, value, dispatcher, tracker, domain):
        try:
            guests = int(value)
            if 1 <= guests <= MAX_GUESTS:
                return {"guests": str(guests)}
        except Exception:
            pass
        dispatcher.utter_message("Please enter a number between 1 and 4.")
        return {"guests": None}

    def validate_room_type(self, value, dispatcher, tracker, domain):
        room_type = normalize_text(value)
        guests = tracker.get_slot("guests")

        if not guests:
            dispatcher.utter_message("Let’s confirm the number of guests first.")
            return {"room_type": None}

        if room_type not in ROOM_CAPACITY:
            dispatcher.utter_message("Available room types: single, double, triple, suite.")
            return {"room_type": None}

        if int(guests) > ROOM_CAPACITY[room_type]:
            dispatcher.utter_message(f"A {room_type} room can host up to {ROOM_CAPACITY[room_type]} guest(s).")
            return {"room_type": None}

        return {"room_type": room_type}

    def validate_breakfast(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if norm in YES_VALUES:
            return {"breakfast": "yes"}
        if norm in NO_VALUES:
            return {"breakfast": "no"}
        dispatcher.utter_message("Please answer yes or no.")
        return {"breakfast": None}

    def validate_payment(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if "credit" in norm:
            return {"payment": "credit card"}
        if "cash" in norm:
            return {"payment": "cash"}
        dispatcher.utter_message("Please choose credit card or cash.")
        return {"payment": None}

    def validate_refund(self, value, dispatcher, tracker, domain):
        norm = normalize_text(value)
        if norm in {"refundable", "non-refundable", "nonrefundable"}:
            return {"refund": norm}
        
        dispatcher.utter_message("Please choose refundable or non-refundable.")
        return {"refund": None}

    def validate_confirmation(self, value, dispatcher, tracker, domain): 
        if value == "yes": 
            return {"confirmation": "yes"} 
        if value == "no": 
            return {"confirmation": "no"}
        dispatcher.utter_message("Please confirm with yes or no.") 
        return {"confirmation": None}

# ============================================================
# CANCEL BOOKING
# ============================================================
class ActionCancelBooking(Action):
    def name(self):
        return "action_cancel_booking"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")
        slots_to_reset = [
            "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment",
            "refund", "confirmation", "booking_field"
        ]

        events = [SlotSet(slot, None) for slot in slots_to_reset]

        events.append(SlotSet("requested_slot", None))
        events.append(ActiveLoop(None))

        return events


# ============================================================
# CONFIRM BOOKING
# ============================================================
class ActionSubmitBookingConfirmed(Action):
    def name(self):
        return "action_submit_booking_confirmed"

    def run(self, dispatcher, tracker, domain):
        confirmation = tracker.get_slot("confirmation")

        if confirmation != "yes":
            dispatcher.utter_message("Your booking has been cancelled. All details were cleared.")
            return [SlotSet(slot, None) for slot in tracker.slots] + [ActiveLoop(None)]

        name = tracker.get_slot("name")

        dispatcher.utter_message(
            f"✅ Thank you {name}, your booking is confirmed! We look forward to welcoming you at our hotel!"
            if name
            else "✅ Your booking is confirmed! We look forward to welcoming you at our hotel!"
        )

        reset_slots = [
            "name", "checkin", "checkout", "guests",
            "room_type", "breakfast", "payment", "refund", "confirmation", "requested_slot"
        ]

        return [SlotSet(slot, None) for slot in reset_slots] + [ActiveLoop(None)]


# ============================================================
# CHANGE BOOKING
# ============================================================
class ActionHandleBookingChange(Action):

    def name(self) -> str:
        return "action_handle_booking_change"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: dict,
    ):
        booking_field = tracker.get_slot("booking_field")

        if not booking_field:
            dispatcher.utter_message(
                "What would you like to change? For example: name, dates, room type, guests, payment, refund or breakfast."
            )
            return []

        # Map booking_field → actual slot name
        slot_mapping = {
            "checkin": "checkin",
            "checkout": "checkout",
            "name": "name",
            "guests": "guests",
            "room": "room_type",
            "breakfast": "breakfast",
            "payment": "payment",
            "refund": "refund",
        }

        slot_to_reset = slot_mapping.get(booking_field)

        if slot_to_reset:
            dispatcher.utter_message(
                f"Okay, let's update your {slot_to_reset}. What is the new value?"
            )
            return [
                SlotSet(slot_to_reset, None),     # clear old value
                SlotSet("requested_slot", slot_to_reset),
                SlotSet("booking_field", None),   # important to avoid loops
            ]

        dispatcher.utter_message("I’m not sure how to change that yet.")
        return []