import asyncio
import sqlite3
import os
from aiogram.types import BotCommand, FSInputFile
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from prices import PriceDatabase, PRICE_DATA
from tokens_i import TOKEN, ADMIN_ID

# --- НАСТРОЙКИ ---
MANAGER_USER = "@fannychka"
CHANNEL_URL = "https://t.me/MLMiyabi"
CHAT_URL = "https://t.me/mlc_squad"
REVIEWS_URL = "https://t.me/myabi7"
MY_TON_WALLET = "@fannychka"
MY_KASPI = "4400430032499250" 
LOGO_PATH = "logo.jpg" 
MY_USDT = "UQCZdm8Q__q_okRyZPnMafcs1RDqb65Cf-4K6oj7uOn0r-dh" 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE INITIALIZATION ---
db = PriceDatabase("shop.db")

def init_db():
    """Initialize database with all tables and populate with prices"""
    db.init_database()
    db.populate_initial_data()

def get_db_prices(region: str, category: str = None):
    """
    Get prices from database
    region: "KZ" or "RU"
    category: None (all), "passes", "bundles", "diamonds", "stars"
    """
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
            SELECT pr.name, p.price
            FROM prices p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.region_id = ? AND pr.category_id = ?
            ORDER BY pr.name
        """, (region, category))
    else:
        cursor.execute("""
            SELECT pr.name, p.price
            FROM prices p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.region_id = ?
            ORDER BY pr.category_id, pr.name
        """, (region,))
    
    results = [(row[0], str(row[1])) for row in cursor.fetchall()]
    conn.close()
    return results

def save_id(uid, val, mode):
    """
    Save user ID or username
    mode: "diamonds" or "stars"
    """
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    if mode == "diamonds":
        cursor.execute("""
            INSERT INTO user_ratings (user_id, game_id) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET game_id=?
        """, (uid, val, val))
    else:
        cursor.execute("""
            INSERT INTO user_ratings (user_id, star_id) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET star_id=?
        """, (uid, val, val))
    
    conn.commit()
    conn.close()

def get_id(uid, mode):
    """
    Get saved user ID or username
    mode: "diamonds" or "stars"
    """
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    
    column = "game_id" if mode == "diamonds" else "star_id"
    result = cursor.execute(f"SELECT {column} FROM user_ratings WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    
    return result[0] if result and result[0] else None

class Order(StatesGroup):
    waiting_for_id = State()
    waiting_for_proof = State()

async def smart_edit(call, text, reply_markup):
    """Edit message or send new one if edit fails"""
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await call.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

def main_kb():
    """Main keyboard with all options"""
    builder = InlineKeyboardBuilder()
    
    # Строка 1: Прайсы
    builder.row(types.InlineKeyboardButton(text="Прайс 🇰🇿", callback_data="price_kz"),
                types.InlineKeyboardButton(text="Прайс 🇷🇺", callback_data="price_ru"))
    
    # Строка 2: Купить алмазы
    builder.row(types.InlineKeyboardButton(text="Купить 🇰🇿", callback_data="buy_kz"),
                types.InlineKeyboardButton(text="Купить 🇷🇺", callback_data="buy_ru"))
    
    # Строка 3: Купить звезды
    builder.row(types.InlineKeyboardButton(text="⭐️ Звёзды 🇰🇿", callback_data="buy_stars_kz"),
                types.InlineKeyboardButton(text="⭐️ Звёзды 🇷🇺", callback_data="buy_stars_ru"))
    
    # Строка 4: Менеджер и Отзывы
    builder.row(types.InlineKeyboardButton(text="Менеджер 👨‍💻", url=f"https://t.me/{MANAGER_USER[1:]}"),
                types.InlineKeyboardButton(text="Отзывы 💌", url=REVIEWS_URL))
    
    # Строка 5: Канал и Чат
    builder.row(types.InlineKeyboardButton(text="Канал 💜", url=CHANNEL_URL),
                types.InlineKeyboardButton(text="Чат 📩", url=CHAT_URL))
    
    builder.adjust(2)
    return builder.as_markup()

@dp.message(Command("start"))
@dp.callback_query(F.data == "to_main")
async def cmd_start(event: types.Union[types.Message, types.CallbackQuery]):
    """Handle /start command and back to main menu"""
    message = event if isinstance(event, types.Message) else event.message
    
    caption_text = "Привет!🥰 В этом боте ты можешь купить алмазы дешево в MLBB.\nВыбери пункт меню:"
    
    if os.path.exists(LOGO_PATH):
        if isinstance(event, types.Message):
            await message.answer_photo(
                photo=FSInputFile(LOGO_PATH),
                caption=caption_text,
                reply_markup=main_kb()
            )
        else:
            try:
                await event.message.edit_caption(
                    caption=caption_text,
                    reply_markup=main_kb()
                )
            except Exception:
                await event.message.answer_photo(
                    photo=FSInputFile(LOGO_PATH),
                    caption=caption_text,
                    reply_markup=main_kb()
                )
            await event.answer()
    else:
        if isinstance(event, types.Message):
            await message.answer(text=caption_text, reply_markup=main_kb())
        else:
            await event.message.edit_text(text=caption_text, reply_markup=main_kb())
            await event.answer()

@dp.callback_query(F.data.startswith("price_"))
async def show_price(call: types.CallbackQuery):
    """Show prices for selected region"""
    reg = call.data.split("_")[1].upper()
    prices = get_db_prices(reg)
    
    currency = PRICE_DATA[reg]["currency"]
    region_name = PRICE_DATA[reg]["region"]
    
    text = f"📊 **ПРАЙС {region_name}:**\n\n"
    for name, price in prices:
        text += f"• {name} — {price} {currency}\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="to_main")
    await smart_edit(call, text, builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def start_buy(call: types.CallbackQuery, state: FSMContext):
    """Show products to buy"""
    data = call.data.split("_")
    
    # Определяем тип товара и регион
    if "stars" in data:
        reg = data[2].upper()
        category = "stars"
        item_type = "stars"
    else:
        reg = data[1].upper()
        category = "diamonds"
        item_type = "diamonds"
    
    prices = get_db_prices(reg, category)
    
    builder = InlineKeyboardBuilder()
    for name, price in prices:
        callback = f"item_stars_{reg}_{name}" if category == "stars" else f"item_{reg}_{name}"
        builder.button(text=f"{name} — {price}", callback_data=callback)
    
    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="🏠 Меню", callback_data="to_main"))
    
    await state.update_data(item_type=item_type)
    await smart_edit(call, f"Выберите товар ({reg}):", builder.as_markup())

@dp.callback_query(F.data.startswith("item"))
async def select_item(call: types.CallbackQuery, state: FSMContext):
    """Select specific item and check for saved ID"""
    parts = call.data.split("_")
    
    # Определяем тип и таблицу
    if "stars" in parts:
        reg = parts[2]
        item_name = "_".join(parts[3:])
        item_type = "stars"
        category = "stars"
    else:
        reg = parts[1]
        item_name = "_".join(parts[2:])
        item_type = "diamonds"
        category = "diamonds"
    
    prices_dict = dict(get_db_prices(reg, category))
    price = prices_dict.get(item_name)
    
    await state.update_data(item=item_name, price=price, reg=reg, type=item_type)
    
    saved = get_id(call.from_user.id, item_type)
    if saved:
        text = f"Ваш ID/Данные: `{saved}`\nИспользовать их?"
        builder = InlineKeyboardBuilder()
        builder.button(text="Да ✅", callback_data="use_saved")
        builder.button(text="Новый ❌", callback_data="input_new")
        await smart_edit(call, text, builder.as_markup())
    else:
        if item_type == "stars":
            prompt = "📝 Введите ваш **Username** (или ID) для начисления звёзд:"
        else:
            prompt = "🎮 Введите ваш **ID и Zone ID**.\nПример: `1234567(1234)`"
        
        await call.message.answer(prompt, parse_mode="Markdown")
        await state.set_state(Order.waiting_for_id)

@dp.message(Order.waiting_for_id)
async def process_id(message: types.Message, state: FSMContext):
    """Process user ID input"""
    data = await state.get_data()
    item_type = data.get("type")

    # Проверка формата для алмазов
    if item_type == "diamonds" and "(" not in message.text:
        await message.answer("❌ Формат: 1234567(1234)")
        return

    save_id(message.from_user.id, message.text, item_type)
    
    await state.update_data(gid=message.text)
    await show_payment(message, state)

@dp.callback_query(F.data == "use_saved")
async def use_saved(call: types.CallbackQuery, state: FSMContext):
    """Use saved ID"""
    data = await state.get_data()
    item_type = data.get("type")
    
    val = get_id(call.from_user.id, item_type)
    await state.update_data(gid=val)
    await show_payment(call.message, state)

@dp.callback_query(F.data == "input_new")
async def input_new_call(call: types.CallbackQuery, state: FSMContext):
    """Input new ID"""
    data = await state.get_data()
    item_type = data.get("type")
    
    if item_type == "stars":
        prompt = "📝 Введите новый **Username**:"
    else:
        prompt = "🎮 Введите новый **ID и Zone ID**.\nПример: `1234567(1234)`"
    
    await call.message.answer(prompt, parse_mode="Markdown")
    await state.set_state(Order.waiting_for_id)

async def show_payment(msg, state):
    """Show payment details"""
    data = await state.get_data()
    icon = "⭐️" if data.get('type') == "stars" else "💠"
    
    currency = PRICE_DATA[data['reg']]["currency"]
    
    text = (f"{icon} Товар: {data['item']}\n"
            f"💰 Цена: {data['price']} {currency}\n"
            f"🎮 ID: `{data['gid']}`\n\n"
            f"**СПОСОБЫ ОПЛАТЫ:**\n\n"
            f"💳 KASPI: `{MY_KASPI}`\n\n"
            f"💰 TON Wallet: `{MY_TON_WALLET}`\n\n"
            f"🪙 USDT (TON):\n`{MY_USDT}`\n\n"
            f"После оплаты пришлите чек.")
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="Открыть Wallet 👛", 
        url="https://t.me/wallet/start")
    )
    builder.row(types.InlineKeyboardButton(
        text="Открыть KASPI 💳", 
        url="https://dz3a4.app.goo.gl/cnNS")
    )
    builder.row(types.InlineKeyboardButton(text="🏠 Отмена", callback_data="to_main"))
    
    if isinstance(msg, types.CallbackQuery):
        msg = msg.message
    
    await msg.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(Order.waiting_for_proof)

@dp.message(Order.waiting_for_proof, F.photo | F.document)
async def finish_order(message: types.Message, state: FSMContext):
    """Finish order and send to admin"""
    data = await state.get_data()
    icon = "⭐️" if data.get('type') == "stars" else "💠"
    
    caption = (f"🚀 НОВЫЙ ЗАКАЗ!\n"
               f"👤 Юзер: @{message.from_user.username}\n"
               f"🎮 ID: {data['gid']}\n"
               f"{icon} Товар: {data['item']}\n"
               f"💰 Сумма: {data['price']}")
    
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    await bot.send_photo(ADMIN_ID, file_id, caption=caption)
    await message.answer("✅ Отправлено! Ожидайте начисления.")
    await state.clear()

async def main():
    """Initialize and run bot"""
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([BotCommand(command="start", description="Запуск")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
