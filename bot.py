import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID, YANDEX_API_KEY, YANDEX_FOLDER_ID, SYSTEM_PROMPT, FREE_LIMIT
from database import init_db, get_user, update_limit, add_history, get_history, clear_history, save_log, get_logs

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ЗАПРОСА К YANDEXGPT ---
async def ask_yandex_gpt(messages):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    yandex_messages = [{"role": "system", "text": SYSTEM_PROMPT}]
    for msg in messages:
        yandex_messages.append({"role": msg["role"], "text": msg["content"]})
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 500},
        "messages": yandex_messages
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                return result['result']['alternatives'][0]['message']['text']
            else:
                err = await response.text()
                logging.error(f"YandexGPT Error: {err}")
                return "Извините, произошла ошибка на сервере. Попробуйте позже."

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await get_user(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Задать вопрос", callback_data="ask")],
        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/koolkrossovki4U")]
    ])
    
    await message.answer(
        f"Здравствуйте! Я AI-консультант салона красоты.\n"
        f"Я могу ответить на вопросы о наших услугах и ценах.\n\n"
        f"У вас осталось {user[0]} бесплатных вопросов.",
        reply_markup=keyboard
    )
    
    if message.from_user.id != ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, f"👤 Новый пользователь: {message.from_user.full_name} (@{message.from_user.username})\nID: {message.from_user.id}")
        except:
            pass

@dp.callback_query(F.data == "ask")
async def ask_question(callback: types.CallbackQuery):
    await callback.message.answer("Напишите ваш вопрос:")
    await callback.answer()

# --- ОСНОВНОЙ ОБРАБОТЧИК ВОПРОСОВ ---
@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    # Проверка лимита
    if user[0] <= 0 and user_id != ADMIN_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/koolkrossovki4U")]
        ])
        await message.answer(
            "⚠️ У вас закончились бесплатные вопросы.\n"
            "Чтобы продолжить консультацию, свяжитесь с нашим менеджером.",
            reply_markup=keyboard
        )
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # 1. Сохраняем вопрос
    await add_history(user_id, "user", message.text)
    history = await get_history(user_id)
    
    # 2. Получаем ответ от YandexGPT
    ai_reply = await ask_yandex_gpt(history)
    
    # 3. Сохраняем ответ в историю и лог
    await add_history(user_id, "assistant", ai_reply)
    await save_log(user_id, message.from_user.username or "unknown", message.text, ai_reply)
    
    # 4. УМЕНЬШАЕМ ЛИМИТ (если это не админ)
    if user_id != ADMIN_ID:
        await update_limit(user_id, -1)
        # Получаем обновленные данные для отображения
        user = await get_user(user_id)
        logging.info(f"Лимит пользователя {user_id} уменьшен. Осталось: {user[0]}")
    
    # 5. Отправляем ответ
    await message.answer(f"{ai_reply}\n\n_(Осталось вопросов: {user[0]})_", parse_mode="Markdown")

# --- АДМИН-КОМАНДЫ ---
@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await clear_history(message.from_user.id)
    await message.answer("Память очищена.")

@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    logs = await get_logs(10)
    if not logs:
        await message.answer("Журнал пуст.")
        return
    
    text = "📋 **Последние запросы:**\n\n"
    for log in logs:
        text += f"👤 {log[0]}: {log[1]}\n🤖 {log[2][:50]}...\n\n"
    await message.answer(text)

async def main():
    await init_db()
    print("Yandex Consultant Bot запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
