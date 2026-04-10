from aiogram.fsm.state import State, StatesGroup


class OperatorTicketStates(StatesGroup):
    reassigning = State()
    writing_note = State()
