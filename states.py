from aiogram.fsm.state import State, StatesGroup


class WaterStates(StatesGroup):
    waiting_for_room = State()
    waiting_for_bringer = State()
    waiting_for_photo_proof = State()


class SwapStates(StatesGroup):
    selecting_swap_type = State()
    # Daily swap states
    selecting_daily_day = State()
    selecting_daily_user = State()
    # Whole Pair swap states
    selecting_pair_target_week = State()
    # Pair proxy swap states
    selecting_proxy_target_user = State()
