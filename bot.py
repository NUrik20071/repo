import asyncio
import sqlite3
import os
from aiogram.types import BotCommand, FSInputFile
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand
from aiogram.exceptions import TelegramBadRequest
from prices import PRODUCTS_KZ, PRODUCTS_RU
from tokens_i import TOKEN, ADMIN_ID

# --- НАСТРОЙКИ ---
MANAGER_USER = "@fannychka"
CHANNEL_URL = "https://t.me/MLMiyabi"
CHAT_URL = "https://t.me/mlc_squad"
REVIEWS_URL = "https://t.me/myabi7"
MY_TON_WALLET = "@fannychka"
LOGO_PATH = "logo.jpg" 
MY_USDT = "UQCZdm8Q__q_okRyZPnMafcs1RDqb65Cf-4K6oj7uOn0r-dh" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- SQL ЛОГИКА ---
from stars_price import STARS_KZ, STARS_RU # Добавь импорт в начало!

def init_db():
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    
    # 1. Сбрасываем и создаем таблицы товаров (как у тебя и было)
    for table in ['products_kz', 'products_ru', 'stars_kz', 'stars_ru']:
        cur.execute(f'DROP TABLE IF EXISTS {table}')
        cur.execute(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT)')
    
    # 2. ИСПРАВЛЕННАЯ ТАБЛИЦА ЮЗЕРОВ
    # Добавляем отдельную колонку star_id для юзернеймов
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                   (user_id INTEGER PRIMARY KEY, 
                    game_id TEXT, 
                    star_id TEXT)''')
    
    # 3. Заливка цен
    cur.executemany("INSERT INTO products_kz (name, price) VALUES (?, ?)", PRODUCTS_KZ)
    cur.executemany("INSERT INTO products_ru (name, price) VALUES (?, ?)", PRODUCTS_RU)
    cur.executemany("INSERT INTO stars_kz (name, price) VALUES (?, ?)", STARS_KZ)
    cur.executemany("INSERT INTO stars_ru (name, price) VALUES (?, ?)", STARS_RU)
    
    conn.commit()
    conn.close()


def get_db_prices(table):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    cur.execute(f"SELECT name, price FROM {table}")
    res = cur.fetchall()
    conn.close()
    return res

def save_id(uid, val, mode):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    if mode == "diamonds":
        # Обновляем только game_id
        cur.execute("INSERT INTO users (user_id, game_id) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET game_id=?", (uid, val, val))
    else:
        # Обновляем только star_id
        cur.execute("INSERT INTO users (user_id, star_id) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET star_id=?", (uid, val, val))
    conn.commit()
    conn.close()

def get_id(uid, mode):
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    column = "game_id" if mode == "diamonds" else "star_id"
    res = cur.execute(f"SELECT {column} FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return res[0] if res and res[0] else None

class Order(StatesGroup):
    waiting_for_id = State()
    waiting_for_proof = State()

async def smart_edit(call, text, reply_markup):
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await call.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

def main_kb():
    builder = InlineKeyboardBuilder()
    # Строка 1: Прайсы
    builder.row(types.InlineKeyboardButton(text="Прайс 🇰🇿", callback_data="price_kz"),
                types.InlineKeyboardButton(text="Прайс 🇷🇺", callback_data="price_ru"))
    
    # Строка 2: Купить алмазы
    builder.row(types.InlineKeyboardButton(text="Купить 🇰🇿", callback_data="buy_kz"),
                types.InlineKeyboardButton(text="Купить 🇷🇺", callback_data="buy_ru"))
    
    # --- ВОТ ЭТОЙ СТРОКИ У ТЕБЯ НЕ ХВАТАЛО ---
    # Строка 3: Купить звезды
    builder.row(types.InlineKeyboardButton(text="⭐️ Звёзды 🇰🇿", callback_data="buy_stars_kz"),
                types.InlineKeyboardButton(text="⭐️ Звёзды 🇷🇺", callback_data="buy_stars_ru"))
    
    # Строка 4: Менеджер и Отзывы
    builder.row(types.InlineKeyboardButton(text="Менеджер 👨‍💻", url=f"https://t.me/{MANAGER_USER[1:]}"),
                types.InlineKeyboardButton(text="Отзывы 💌", url=REVIEWS_URL))
    
    # Строка 5: Канал и Чат
    builder.row(types.InlineKeyboardButton(text="Канал 💜", url=CHANNEL_URL),
                types.InlineKeyboardButton(text="Чат 📩", url=CHAT_URL))
    
    builder.adjust(2) # Выравниваем по 2 кнопки в ряд
    return builder.as_markup()

@dp.message(Command("start"))
@dp.callback_query(F.data == "to_main") # Добавляем, чтобы кнопка "Назад" тоже работала тут
async def cmd_start(event: types.Union[types.Message, types.CallbackQuery]):
    # Определяем, откуда пришло событие: из сообщения или из кнопки
    message = event if isinstance(event, types.Message) else event.message
    
    caption_text = "Привет!🥰 В этом боте ты можешь купить алмазы дешево в MLBB.\nВыбери пункт меню:"
    
    if os.path.exists(LOGO_PATH):
        # Если это сообщение (/start), отправляем новое фото
        if isinstance(event, types.Message):
            await message.answer_photo(
                photo=FSInputFile(LOGO_PATH),
                caption=caption_text,
                reply_markup=main_kb()
            )
        else:
            # Если это кнопка (Callback), пытаемся отредактировать старое фото
            try:
                await event.message.edit_caption(
                    caption=caption_text,
                    reply_markup=main_kb()
                )
            except Exception:
                # Если не получилось (например, старое сообщение было без фото), просто шлем новое
                await event.message.answer_photo(
                    photo=FSInputFile(LOGO_PATH),
                    caption=caption_text,
                    reply_markup=main_kb()
                )
                await event.answer()
    else:
        # Если файла logo.jpg нет, шлем просто текст
        if isinstance(event, types.Message):
            await message.answer(text=caption_text, reply_markup=main_kb())
        else:
            await event.message.edit_text(text=caption_text, reply_markup=main_kb())
            await event.answer()
            
@dp.callback_query(F.data.startswith("price_"))
        
async def show_price(call: types.CallbackQuery):
    reg = call.data.split("_")[1]
    prices = get_db_prices(f"products_{reg}")
    text = f"📊 **ПРАЙС {'🇷🇺' if reg == 'ru' else '🇰🇿'}:**\n\n"
    for n, p in prices:
        text += f"• {n} — {p}\n"
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="to_main")
    await smart_edit(call, text, builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def start_buy(call: types.CallbackQuery, state: FSMContext):
    data = call.data.split("_")
    # Если нажали "buy_stars_kz", в списке будет "stars"
    if "stars" in data:
        reg = data[2]
        prefix = "item_stars" # Индекс для звезд
    else:
        reg = data[1]
        prefix = "item" # Старый индекс для алмазов

    table = f"stars_{reg}" if "stars" in data else f"products_{reg}"
    prices = get_db_prices(table)
    
    builder = InlineKeyboardBuilder()
    for name, price in prices:
        # Генерируем callback с нужным префиксом
        builder.button(text=f"{name} — {price}", callback_data=f"{prefix}_{reg}_{name}")
    
    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="🏠 Меню", callback_data="to_main"))
    await smart_edit(call, f"Выберите товар ({reg.upper()}):", builder.as_markup())

@dp.callback_query(F.data.startswith("item"))
async def select_item(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
    
    # Определяем тип и таблицу
    if "stars" in parts:
        # Индексы для: item_stars_kz_название
        reg, item_name = parts[2], parts[3]
        table, item_type = f"stars_{reg}", "stars"
    else:
        # Индексы для: item_kz_название
        reg, item_name = parts[1], parts[2]
        table, item_type = f"products_{reg}", "diamonds"
    
    prices_dict = dict(get_db_prices(table))
    price = prices_dict.get(item_name)
    
    # ВАЖНО: сохраняем type в state, чтобы process_id его видел
    await state.update_data(item=item_name, price=price, reg=reg, type=item_type)
    
    saved = get_id(call.from_user.id, item_type)
    if saved:
        # Если ID сохранен, спрашиваем, юзать ли его
        text = f"Ваш ID/Данные: `{saved}`\nИспользовать их?"
        builder = InlineKeyboardBuilder()
        builder.button(text="Да ✅", callback_data="use_saved")
        builder.button(text="Новый ❌", callback_data="input_new")
        await smart_edit(call, text, builder.as_markup())
    else:
        # ВОТ ТУТ МЕНЯЕМ ТЕКСТ
        if item_type == "stars":
            prompt = "📝 Введите ваш **Username** (или ID) для начисления звёзд:"
        else:
            prompt = "🎮 Введите ваш **ID и Zone ID**.\nПример: `1234567(1234)`"
            
        await call.message.answer(prompt, parse_mode="Markdown")
        await state.set_state(Order.waiting_for_id)


@dp.message(Order.waiting_for_id)
async def process_id(message: types.Message, state: FSMContext):
    data = await state.get_data()
    m = data.get("type") # Получаем 'diamonds' или 'stars'

    # Проверка для алмазов
    if m == "diamonds" and "(" not in message.text:
        await message.answer("❌ Формат: 1234567(1234)")
        return

    # ПЕРЕДАЕМ ТРЕТИЙ АРГУМЕНТ (m)
    save_id(message.from_user.id, message.text, m) 
    
    await state.update_data(gid=message.text)
    await show_payment(message, state)


@dp.callback_query(F.data == "use_saved")
async def use_saved(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_type = data.get("type") # diamonds или stars
    
    val = get_id(call.from_user.id, item_type) # Добавили аргумент
    await state.update_data(gid=val)
    await show_payment(call.message, state)

@dp.callback_query(F.data == "input_new")
async def input_new_call(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новый ID и Zone ID:")
    await state.set_state(Order.waiting_for_id)

async def show_payment(msg, state):
    data = await state.get_data()
    # Выбираем иконку в зависимости от типа товара
    icon = "⭐️" if data.get('type') == "stars" else "💠"
    
    text = (f"{icon} Товар: {data['item']}\n"
            f"💰 Цена: {data['price']}\n"
            f"🎮 ID: `{data['gid']}`\n\n"
            # ... остальной текст
            f"Сделайте перевод на кошелек:`{MY_TON_WALLET}`\n\n"
            f"Или на адрес криптокошелька USDT (TON):\n `{MY_USDT}`\n\n"
            f"После оплаты пришли скриншот чека.")
    
    builder = InlineKeyboardBuilder()
    # Теперь кнопка открывает Mini App Wallet
    builder.row(types.InlineKeyboardButton(
        text="Открыть Wallet 👛", 
        url="https://t.me/wallet/start")
    )
    builder.row(types.InlineKeyboardButton(text="🏠 Отмена", callback_data="to_main"))
    
    if isinstance(msg, types.CallbackQuery): msg = msg.message
    await msg.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(Order.waiting_for_proof)

@dp.message(Order.waiting_for_proof, F.photo | F.document)
async def finish_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    caption = f"🚀 ЗАКАЗ!\nЮзер: @{message.from_user.username}\nID: {data['gid']}\nТовар: {data['item']} ({data['price']})"
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    await bot.send_photo(ADMIN_ID, file_id, caption=caption)
    await message.answer("✅ Отправлено! Ожидайте начисления.")
    await state.clear()

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([BotCommand(command="start", description="Запуск")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())