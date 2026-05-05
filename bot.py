import asyncio
import sqlite3
import os
from aiohttp import web
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
MY_KASPI = "4400430032499250"
LOGO_PATH = "logo.jpg"
MY_USDT = "DCEYimfLyMs4r89Dmw1QGKkYqFVbwhvScvGgcjgX93ec"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE INITIALIZATION ---
db = PriceDatabase("shop.db")

def init_db():
    db.init_database()
    db.populate_initial_data()
    _init_referral_tables()

def _init_referral_tables():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER PRIMARY KEY,
            referred_by INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            game_id TEXT,
            item TEXT NOT NULL,
            price INTEGER NOT NULL,
            currency TEXT NOT NULL,
            region TEXT NOT NULL,
            item_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS referral_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(referrer_id, order_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance_kz INTEGER NOT NULL DEFAULT 0,
            balance_ru INTEGER NOT NULL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add missing columns to existing users table
    c.execute("PRAGMA table_info(users)")
    existing = [row[1] for row in c.fetchall()]
    if 'username' not in existing:
        c.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if 'updated_at' not in existing:
        c.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP")
    conn.commit()
    conn.close()

# --- PRICE HELPERS ---

def get_db_prices(region: str, category: str = None):
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if category:
        cursor.execute("""
            SELECT COALESCE(p.name, pr.name) AS name, p.price
            FROM prices p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.region_id = ? AND pr.category_id = ?
            ORDER BY pr.display_order, pr.id
        """, (region, category))
    else:
        cursor.execute("""
            SELECT COALESCE(p.name, pr.name) AS name, p.price
            FROM prices p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.region_id = ?
            ORDER BY pr.display_order, pr.id
        """, (region,))
    results = [(row[0], str(row[1])) for row in cursor.fetchall()]
    conn.close()
    return results

# --- USER DATA HELPERS ---

def save_id(uid, val, mode):
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
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    column = "game_id" if mode == "diamonds" else "star_id"
    result = cursor.execute(
        f"SELECT {column} FROM user_ratings WHERE user_id=?", (uid,)
    ).fetchone()
    conn.close()
    return result[0] if result and result[0] else None

# --- REFERRAL HELPERS ---

def save_referral(user_id: int, referred_by: int):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO referrals (user_id, referred_by) VALUES (?, ?)",
        (user_id, referred_by)
    )
    conn.commit()
    conn.close()

def get_referrer(user_id: int):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    result = c.execute(
        "SELECT referred_by FROM referrals WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return result[0] if result else None

def get_referral_stats(user_id: int):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    count = c.execute(
        "SELECT COUNT(*) FROM referrals WHERE referred_by=?", (user_id,)
    ).fetchone()[0]
    balance = c.execute(
        "SELECT balance_kz, balance_ru FROM balances WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    balance_kz = balance[0] if balance else 0
    balance_ru = balance[1] if balance else 0
    return count, balance_kz, balance_ru

def save_user(user_id: int, username: str):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, username, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, username or str(user_id)))
    conn.commit()
    conn.close()

def get_all_balances():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    rows = c.execute("""
        SELECT b.user_id,
               COALESCE(u.username, CAST(b.user_id AS TEXT)) as username,
               b.balance_kz, b.balance_ru,
               (SELECT COUNT(*) FROM referrals WHERE referred_by = b.user_id) as ref_count
        FROM balances b
        LEFT JOIN users u ON u.user_id = b.user_id
        WHERE b.balance_kz > 0 OR b.balance_ru > 0
        ORDER BY (b.balance_kz + b.balance_ru) DESC
    """).fetchall()
    conn.close()
    return rows

def get_order_stats():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    total   = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    done    = c.execute("SELECT COUNT(*) FROM orders WHERE status='confirmed'").fetchone()[0]
    conn.close()
    return total, pending, done

# --- ORDER HELPERS ---

def save_order(user_id, username, game_id, item, price, currency, region, item_type) -> int:
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO orders (user_id, username, game_id, item, price, currency, region, item_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, game_id, item, int(price), currency, region, item_type))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    return order_id

def confirm_order_db(order_id: int):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET status='confirmed', confirmed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
        (order_id,)
    )
    result = c.execute(
        "SELECT user_id, price, currency, region FROM orders WHERE id=?", (order_id,)
    ).fetchone()
    conn.commit()
    conn.close()
    return result

def add_referral_earning(referrer_id: int, order_id: int, amount: int, currency: str):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO referral_earnings (referrer_id, order_id, amount, currency)
        VALUES (?, ?, ?, ?)
    """, (referrer_id, order_id, amount, currency))
    if currency == '₸':
        c.execute("""
            INSERT INTO balances (user_id, balance_kz) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance_kz = balance_kz + excluded.balance_kz
        """, (referrer_id, amount))
    else:
        c.execute("""
            INSERT INTO balances (user_id, balance_ru) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance_ru = balance_ru + excluded.balance_ru
        """, (referrer_id, amount))
    conn.commit()
    conn.close()

# --- FSM STATES ---

class Order(StatesGroup):
    waiting_for_id = State()
    waiting_for_proof = State()
    waiting_for_confirm = State()

# --- UI HELPERS ---

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
    builder.row(
        types.InlineKeyboardButton(text="Прайс 🇰🇿", callback_data="price_kz"),
        types.InlineKeyboardButton(text="Прайс 🇷🇺", callback_data="price_ru")
    )
    builder.row(
        types.InlineKeyboardButton(text="💎 Купить 🇰🇿", callback_data="buy_kz"),
        types.InlineKeyboardButton(text="💎 Купить 🇷🇺", callback_data="buy_ru")
    )
    builder.row(
        types.InlineKeyboardButton(text="⭐️ Звёзды 🇰🇿", callback_data="buy_stars_kz"),
        types.InlineKeyboardButton(text="⭐️ Звёзды 🇷🇺", callback_data="buy_stars_ru")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔗 Рефералы", callback_data="referral_info")
    )
    builder.row(
        types.InlineKeyboardButton(text="Менеджер 👨‍💻", url=f"https://t.me/{MANAGER_USER[1:]}"),
        types.InlineKeyboardButton(text="Отзывы 💌", url=REVIEWS_URL)
    )
    builder.row(
        types.InlineKeyboardButton(text="Канал 💜", url=CHANNEL_URL),
        types.InlineKeyboardButton(text="Чат 📩", url=CHAT_URL)
    )
    return builder.as_markup()

# --- HANDLERS ---

@dp.message(Command("start"))
@dp.callback_query(F.data == "to_main")
async def cmd_start(event: types.Union[types.Message, types.CallbackQuery]):
    user = event.from_user
    save_user(user.id, user.username)

    if isinstance(event, types.Message):
        args = event.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1][4:])
                if referrer_id != user.id:
                    save_referral(user.id, referrer_id)
            except ValueError:
                pass

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

PRICE_SECTIONS = [
    ("🎫 Пропуски", ["passes", "bundles"]),
    ("💎 Алмазы", ["diamonds"]),
    ("⭐ Звёзды", ["stars"]),
]

@dp.callback_query(F.data.startswith("price_"))
async def show_price(call: types.CallbackQuery):
    reg = call.data.split("_")[1].upper()
    currency = PRICE_DATA[reg]["currency"]
    region_name = PRICE_DATA[reg]["region"]

    text = f"📊 **ПРАЙС {region_name}:**\n\n"
    for header, categories in PRICE_SECTIONS:
        items = []
        for category in categories:
            items.extend(get_db_prices(reg, category))
        if not items:
            continue
        text += f"**{header}**\n"
        for name, price in items:
            text += f"• {name} — {price} {currency}\n"
        text += "\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="to_main")
    await smart_edit(call, text, builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def start_buy(call: types.CallbackQuery, state: FSMContext):
    data = call.data.split("_")
    if "stars" in data:
        reg = data[2].upper()
        category = "stars"
        item_type = "stars"
    else:
        reg = data[1].upper()
        category = "diamonds"
        item_type = "diamonds"

    prices = get_db_prices(reg, category)
    currency = PRICE_DATA[reg]["currency"]

    builder = InlineKeyboardBuilder()
    for name, price in prices:
        callback = f"item_stars_{reg}_{name}" if category == "stars" else f"item_{reg}_{name}"
        builder.button(text=f"{name} — {price} {currency}", callback_data=callback)

    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(text="🏠 Меню", callback_data="to_main"))

    await state.update_data(item_type=item_type)
    await smart_edit(call, f"Выберите товар ({reg}):", builder.as_markup())

@dp.callback_query(F.data.startswith("item"))
async def select_item(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
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
    data = await state.get_data()
    item_type = data.get("type")

    if item_type == "diamonds" and "(" not in message.text:
        await message.answer("❌ Формат: 1234567(1234)")
        return

    save_id(message.from_user.id, message.text, item_type)
    await state.update_data(gid=message.text)
    await show_payment(message, state)

@dp.callback_query(F.data == "use_saved")
async def use_saved(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    val = get_id(call.from_user.id, data.get("type"))
    await state.update_data(gid=val)
    await show_payment(call.message, state)

@dp.callback_query(F.data == "input_new")
async def input_new_call(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_type = data.get("type")
    if item_type == "stars":
        prompt = "📝 Введите новый **Username**:"
    else:
        prompt = "🎮 Введите новый **ID и Zone ID**.\nПример: `1234567(1234)`"
    await call.message.answer(prompt, parse_mode="Markdown")
    await state.set_state(Order.waiting_for_id)

async def show_payment(msg, state):
    data = await state.get_data()
    icon = "⭐️" if data.get('type') == "stars" else "💠"
    currency = PRICE_DATA[data['reg']]["currency"]

    text = (f"{icon} Товар: {data['item']}\n"
            f"💰 Цена: {data['price']} {currency}\n"
            f"🎮 ID: `{data['gid']}`\n\n"
            f"**СПОСОБЫ ОПЛАТЫ:**\n\n"
            f"💳 KASPI: `{MY_KASPI}`\n\n"
            f"🪙 USDT (SOL):\n`{MY_USDT}`\n\n"
            f"После оплаты пришлите чек.")

    builder = InlineKeyboardBuilder()
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
async def receive_proof(message: types.Message, state: FSMContext):
    """Получили файл — показываем подтверждение пользователю."""
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    is_photo = bool(message.photo)
    await state.update_data(proof_file_id=file_id, proof_is_photo=is_photo)
    await state.set_state(Order.waiting_for_confirm)

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Да, отправить", callback_data="proof_send"),
        types.InlineKeyboardButton(text="🔄 Отправить другой", callback_data="proof_retry")
    )
    await message.answer(
        "Это ваш чек? Проверьте и подтвердите отправку.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "proof_send")
async def proof_send(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Пользователь подтвердил чек — отправляем админу."""
    data = await state.get_data()
    icon = "⭐️" if data.get('type') == "stars" else "💠"
    currency = PRICE_DATA[data['reg']]["currency"]

    order_id = save_order(
        user_id=call.from_user.id,
        username=call.from_user.username or str(call.from_user.id),
        game_id=data['gid'],
        item=data['item'],
        price=data['price'],
        currency=currency,
        region=data['reg'],
        item_type=data.get('type')
    )

    caption = (f"🚀 НОВЫЙ ЗАКАЗ #{order_id}\n"
               f"👤 Юзер: @{call.from_user.username}\n"
               f"🎮 ID: {data['gid']}\n"
               f"{icon} Товар: {data['item']}\n"
               f"💰 Сумма: {data['price']} {currency}")

    admin_kb = InlineKeyboardBuilder()
    admin_kb.button(text="✅ Подтвердить", callback_data=f"confirm_ask_{order_id}")

    file_id = data['proof_file_id']
    if data.get('proof_is_photo'):
        await bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=admin_kb.as_markup())
    else:
        await bot.send_document(ADMIN_ID, file_id, caption=caption, reply_markup=admin_kb.as_markup())

    await call.message.edit_text("✅ Чек отправлен! Ожидайте подтверждения.")
    await state.clear()

@dp.callback_query(F.data == "proof_retry")
async def proof_retry(call: types.CallbackQuery, state: FSMContext):
    """Пользователь хочет отправить другой файл."""
    await state.set_state(Order.waiting_for_proof)
    await call.message.edit_text("📎 Отправьте правильный чек (фото или файл):")

# --- ADMIN: ДВУХШАГОВОЕ ПОДТВЕРЖДЕНИЕ ---

@dp.callback_query(F.data.startswith("confirm_ask_"))
async def confirm_ask(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    order_id = call.data.split("_")[2]
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="Да, подтвердить ✅", callback_data=f"confirm_yes_{order_id}"),
        types.InlineKeyboardButton(text="Нет ❌", callback_data=f"confirm_no_{order_id}")
    )
    base = call.message.caption or ""
    await call.message.edit_caption(
        caption=base + "\n\n⚠️ Вы уверены, что хотите подтвердить заказ?",
        reply_markup=builder.as_markup()
    )
    await call.answer()

@dp.callback_query(F.data.startswith("confirm_yes_"))
async def confirm_yes(call: types.CallbackQuery, bot: Bot):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    order_id = int(call.data.split("_")[2])
    result = confirm_order_db(order_id)
    if not result:
        await call.answer("❌ Заказ уже подтверждён или не найден", show_alert=True)
        return

    user_id, price, currency, region = result

    referrer_id = get_referrer(user_id)
    bonus_text = ""
    if referrer_id:
        bonus = max(1, int(price) * 5 // 100)
        add_referral_earning(referrer_id, order_id, bonus, currency)
        bonus_text = f"\n💰 Реферал: +{bonus} {currency}"
        try:
            await bot.send_message(
                referrer_id,
                f"💰 Ваш реферал совершил покупку!\n"
                f"Вам начислено: *{bonus} {currency}*",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    try:
        await bot.send_message(user_id, "✅ Ваш заказ подтверждён! Спасибо за покупку 🎉")
    except Exception:
        pass

    base = (call.message.caption or "").split("\n\n⚠️")[0]
    await call.message.edit_caption(
        caption=base + f"\n\n✅ Подтверждено{bonus_text}",
        reply_markup=None
    )
    await call.answer("✅ Заказ подтверждён")

@dp.callback_query(F.data.startswith("confirm_no_"))
async def confirm_no(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    order_id = call.data.split("_")[2]
    base = (call.message.caption or "").split("\n\n⚠️")[0]
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_ask_{order_id}")
    await call.message.edit_caption(caption=base, reply_markup=builder.as_markup())
    await call.answer("Отменено")

# --- ADMIN PANEL ---

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total, pending, done = get_order_stats()
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💰 Рефералы и балансы", callback_data="admin_balances"))
    builder.row(types.InlineKeyboardButton(text="📦 Статистика заказов", callback_data="admin_orders"))
    await message.answer(
        f"🛠 *Админ-панель*\n\n"
        f"📦 Заказов всего: *{total}*\n"
        f"⏳ Ожидают подтверждения: *{pending}*\n"
        f"✅ Подтверждено: *{done}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_balances")
async def admin_balances(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    rows = get_all_balances()
    if not rows:
        text = "🛠 *Балансы рефералов*\n\nПока нет начислений."
    else:
        lines = ["🛠 *Балансы рефералов*\n"]
        for i, (uid, username, kz, ru, ref_count) in enumerate(rows, 1):
            parts = []
            if kz:
                parts.append(f"{kz} ₸")
            if ru:
                parts.append(f"{ru} ₽")
            balance_str = " / ".join(parts)
            lines.append(f"{i}. @{username} — {balance_str} (рефералов: {ref_count})")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    total, pending, done = get_order_stats()
    text = (
        f"📦 *Статистика заказов*\n\n"
        f"Всего: *{total}*\n"
        f"⏳ Ожидают: *{pending}*\n"
        f"✅ Выполнено: *{done}*"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    total, pending, done = get_order_stats()
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💰 Рефералы и балансы", callback_data="admin_balances"))
    builder.row(types.InlineKeyboardButton(text="📦 Статистика заказов", callback_data="admin_orders"))
    await call.message.edit_text(
        f"🛠 *Админ-панель*\n\n"
        f"📦 Заказов всего: *{total}*\n"
        f"⏳ Ожидают подтверждения: *{pending}*\n"
        f"✅ Подтверждено: *{done}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await call.answer()

# --- РЕФЕРАЛЬНАЯ ПРОГРАММА ---

@dp.callback_query(F.data == "referral_info")
async def referral_info(call: types.CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    user_id = call.from_user.id
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    count, balance_kz, balance_ru = get_referral_stats(user_id)

    balance_lines = ""
    if balance_kz:
        balance_lines += f"💰 Баланс KZ: *{balance_kz} ₸*\n"
    if balance_ru:
        balance_lines += f"💰 Баланс RU: *{balance_ru} ₽*\n"
    if not balance_lines:
        balance_lines = "Пока нет начислений\n"

    text = (
        f"🔗 *Реферальная программа*\n\n"
        f"Приглашайте друзей и получайте *5%* от каждой их покупки!\n\n"
        f"👥 Приглашено: *{count}* чел.\n"
        f"{balance_lines}\n"
        f"Ваша ссылка:\n`{ref_link}`"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="to_main")
    await smart_edit(call, text, builder.as_markup())

# --- HEALTH CHECK SERVER (для UptimeRobot) ---

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def run_health_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# --- ЗАПУСК ---

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([BotCommand(command="start", description="Запуск")])
    await asyncio.gather(
        run_health_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
