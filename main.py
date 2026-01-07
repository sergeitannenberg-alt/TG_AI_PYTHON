import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
import config


bot = Bot(token=config.TG_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = OpenAI(
    api_key=config.AI_TOKEN,
    base_url="https://openrouter.ai/api/v1"
)


class IN_CHAT(StatesGroup):
    in_chat = State()


USER_MEMORY = {}




USER_BUTTONS = {
    "chat": {
        "text": "Поболтать",
        "model": "mistralai/devstral-2512:free",
        "system": "Ты дружелюбный, умный собеседник",
        "mode": "chat",
        "max_tokens": 500,
        "temperature": 0.7
    },
    "fact": {
        "text": "Интересный факт",
        "model": "mistralai/devstral-2512:free",
        "system": "Ты эксперт по науке и фактам",
        "prompt": "Расскажи один интересный научный факт",
        "mode": "single",
        "max_tokens": 200,
        "temperature": 0.4
    },
    "persons":{
        "text": "Разговор с известной личностью",
        "mode": "submenu"
    }
}

PERSONS= {
    "elon": {
            "text": "Илон Маск",
            "mode": "chat",
            "model": "mistralai/devstral-2512:free",
            "system": (
                "Ты — Илон Маск. "
                "Разговаривай дерзко, уверенно, как визионер."
            ),
            "temperature": 0.7,
            "max_tokens": 500
        },

        "einstein": {
            "text": "Альберт Эйнштейн",
            "mode": "chat",
            "model": "mistralai/devstral-2512:free",
            "system": (
                "Ты — Альберт Эйнштейн. "
                "Объясняй сложное просто, философствуй."
            ),
            "temperature": 0.5,
            "max_tokens": 500
        }
}
def menu_kb():

    kb = InlineKeyboardBuilder()

    for key, cfg in USER_BUTTONS.items():
        kb.button(
            text=cfg["text"],
            callback_data=f"menu:{key}"
        )
    kb.adjust(1)
    return kb.as_markup()

def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(
        text= "Назад",
        callback_data="back_button"
    )
    return kb.as_markup()
def persons_kb():
    kb = InlineKeyboardBuilder()
    for key, cfg in PERSONS.items():
        kb.button(
            text=cfg["text"],
            callback_data=f"person:{key}"

        )
    kb.adjust(1)
    return kb.as_markup()

def fact_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Ещё факт", callback_data="fact_more")
    kb.button(text="Назад", callback_data="back_button")
    kb.adjust(1)
    return kb.as_markup()

def ai_requests(config:dict, user_id:int, user_text:str | None= None) -> str:
    if user_id not in USER_MEMORY:
        USER_MEMORY[user_id] = [
            {"role":"system", "content":config["system"]}
        ]

    messages = USER_MEMORY[user_id]

    if config["mode"] == "single":
        temp_messages = messages + [
            {"role":"user", "content": config["prompt"]}
        ]

        resource = client.chat.completions.create(
            model= config["model"],
            messages= temp_messages,
            max_tokens=config["max_tokens"],
            temperature= config["temperature"],
        )

        return resource.choices[0].message.content.strip()

    if config["mode"] == "chat" and user_text:
        messages.append({"role": "user", "content":user_text})

        resource= client.chat.completions.create(
            model=config["model"],
            messages = messages,
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )

        answer = resource.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": answer})

        return answer
    return ""



@dp.message(Command(commands=["start"]))
async def start(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == IN_CHAT.in_chat.state:
        await message.answer("Сначала выйди из текущего чата, нажми 'Назад' ")
        return

    await state.clear()
    await message.answer("Привет! Выбери действие:", reply_markup=menu_kb())


@dp.callback_query(F.data.startswith("menu:"))
async def menu_handler(call:CallbackQuery,state:FSMContext):
    await call.answer()
    action = call.data.split(":")[1]
    config = USER_BUTTONS[action]
    if await state.get_state() == IN_CHAT.in_chat.state:
        await call.answer("Сначала выйди из текущего чата, нажми 'Назад'", show_alert=True)
        return

    if config["mode"] == "single":
        await state.set_state(IN_CHAT.in_chat)
        await state.update_data(active_config=config)

        text = ai_requests(config, call.from_user.id)

        await call.message.edit_text(text, reply_markup=fact_kb())
        return

    if config["mode"] == "chat":
        await state.set_state(IN_CHAT.in_chat)
        await state.update_data(active_config= config)
        USER_MEMORY[call.from_user.id]= [
            {"role": "system", "content": config["system"]}
        ]
        photo = FSInputFile("images/menu.jpg")
        await call.message.answer_photo(
            photo=photo,
            caption="привет, о чём поболтаем",
            reply_markup=back_button()
        )
        return
    if config["mode"] == "submenu":
        await call.message.edit_text(
            text="Выбери персонажа",
            reply_markup=persons_kb(),
        )
        return
    else:
        text = ai_requests(config,call.from_user.id)
        await call.message.edit_text(text, reply_markup=back_button())

@dp.callback_query(F.data.startswith("person:"))
async def person_handler(call:CallbackQuery,state:FSMContext):
    await call.answer()
    key = call.data.split(":")[1]
    config_person = PERSONS[key]
    user_id = call.from_user.id

    USER_MEMORY[user_id] = [
        {"role": "system", "content": config_person["system"]}
    ]

    await state.set_state(IN_CHAT.in_chat)
    await state.update_data(active_config= config_person)
    await call.message.edit_text(
        text=f"Ты общаешься с {config_person['text']}",
        reply_markup=back_button()
    )
@dp.callback_query(F.data == "fact_more")
async def more_fact(call: CallbackQuery, state: FSMContext):


    data = await state.get_data()
    config = data.get("active_config")

    if not config or config["mode"] != "single":
        await call.message.edit_text(
            "Возвращаемся в меню",
            reply_markup=menu_kb()
        )
        await state.clear()
        return

    text = ai_requests(config, call.from_user.id)

    await call.message.edit_text(
        text,
        reply_markup=fact_kb()
    )

@dp.callback_query(F.data == "back_button")
async def back_henbler(call:CallbackQuery,state:FSMContext):
    await call.answer()
    user_id= call.from_user.id
    await state.clear()
    USER_MEMORY.pop(user_id,None)
    await call.message.answer(
        text="Главное меню",
        reply_markup=menu_kb()
    )
@dp.message(IN_CHAT.in_chat)
async def chat_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    config = data.get("active_config")

    if not config:
        await message.answer("Ошибка конфигурации. Возвращаемся в меню.", reply_markup=menu_kb())
        await state.clear()
        USER_MEMORY.pop(user_id, None)
        return

    if config["mode"] == "single":
        await message.answer(
            "Для фактов используй кнопки 👇",
            reply_markup=fact_kb()
        )
        return

    answer = ai_requests(config, user_id, message.text)
    await message.answer(answer, reply_markup=back_button())



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())