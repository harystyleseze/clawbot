from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    awaiting_date = State()
    awaiting_time = State()
    awaiting_party_size = State()
    awaiting_confirmation = State()
    awaiting_deposit = State()
