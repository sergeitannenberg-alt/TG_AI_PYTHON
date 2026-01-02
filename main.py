import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from openai import OpenAI
import config



bot = Bot(token=config.TG_TOKEN)
dp = Dispatcher()
client = OpenAI(
    api_key=config.AI_TOKEN,
    base_url="https://openrouter.ai/api/v1"
)


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
        "temperature": 0.5
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



@dp.message(CommandStart)
async def start(message:Message):
    await message.answer("Hello", reply_markup=menu_kb())


@dp.callback_query(F.data.startswith("menu:"))
async def menu_handler(call:CallbackQuery):
    action = call.data.split(":")[1]
    if action == "fact":
        await call.answer("Думаю 🤔")  # ← СРАЗУ отвечаем Telegram

        cfg = USER_BUTTONS["fact"]

        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": cfg["system"]},
                {"role": "user", "content": cfg["prompt"]},
            ],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
        )

        fact_text = response.choices[0].message.content.strip()

        await call.message.edit_text(
            f"🔬 Интересный факт:\n\n{fact_text}",
            reply_markup=back_button()
        )
        return


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())