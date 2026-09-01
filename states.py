from aiogram.fsm.state import State, StatesGroup


class WaterStates(StatesGroup):
    waiting_for_bringer = State()
    waiting_for_photo_proof = State()


class SwapStates(StatesGroup):
    selecting_target_day = State()
    selecting_target_user = State()
