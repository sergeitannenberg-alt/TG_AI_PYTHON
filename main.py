import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from openai import OpenAI
from pyexpat.errors import messages

import config



bot = Bot(token=config.TG_TOKEN)
dp = Dispatcher()
client = OpenAI(
    api_key=config.AI_TOKEN,
    base_url="https://openrouter.ai/api/v1"
)

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
}
def menu_kb():

    kb = InlineKeyboardBuilder()

    for key, cfg in USER_BUTTONS.items():
        kb.button(
            text=cfg["text"],
            callback_data=f"menu:{key}"
        )

    return kb.as_markup()

def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(
        text= "Назад",
        callback_data="back_button"
    )
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



@dp.message(CommandStart)
async def start(message:Message):
    await message.answer("Hello", reply_markup=menu_kb())


@dp.callback_query(F.data.startswith("menu:"))
async def menu_handler(call:CallbackQuery):
    action = call.data.split(":")[1]
    config = USER_BUTTONS[action]
    if config["mode"] == "chat":
        USER_MEMORY[call.from_user.id]= [
            {"role": "system", "content": config["system"]}
        ]
        await call.message.edit_text(
            "привет, о чём поболтаем",
            reply_markup=back_button()
        )
        return
    text = ai_requests(config,call.from_user.id)
    await call.message.edit_text(text, reply_markup=back_button())



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())