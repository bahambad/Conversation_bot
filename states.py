from aiogram.fsm.state import StatesGroup, State

class Avangard(StatesGroup):
    volume = State()
    song = State()
    transforming = State()

class Vtovoice(StatesGroup):
    getting_processing = State()

class Video_processing(StatesGroup):
    choosing_option = State()