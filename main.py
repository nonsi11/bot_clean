from aiogram.types import InlineKeyboardMarkup
import asyncio
import time as _t
from collections import defaultdict
import logging
import time
import random

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message

from config import (
    BOT_TOKEN, ADMIN_IDS, BONUS_COOLDOWN, BONUS_AMOUNT, REFERRAL_BONUS
)
from database import set_nick, clear_nick, set_show_nick
from database import deposit_clan
from database import get_clan_by_user, create_clan, get_clan_members, deposit_clan, get_clan_top, leave_clan
from database import (
    init_db, ensure_user, set_agreed, is_agreed,
    get_balance, update_balance, get_user, add_bet_stats, add_history,
    get_history, get_history_count, get_top_players,
    set_referrer, get_referrals_count, get_last_bonus, set_last_bonus,
    get_last_bet, set_last_bet, get_referrals_list,
    add_gift, get_gifts_received, get_gifts_sent, find_user_by_id,
    get_jackpot, add_to_jackpot, claim_jackpot,
    ACHIEVEMENTS, unlock_achievement, get_user_achievements,
    create_duel, get_duel, join_duel, finish_duel, cancel_duel, get_user_duels,
    set_duel_rolls, set_duel_side,
    get_game_stats, get_total_stats, cleanup_old_history,
    is_banned, set_banned, get_all_user_ids, bot_stats,
    create_promo, delete_promo, list_promos, use_promo,
    VIP_PRICES, VIP_MULTIPLIER, VIP_BONUS, VIP_NAMES, VIP_COOLDOWN, get_vip, set_vip,
)
from keyboards import settings_kb
from keyboards import (
    agreement_kb, main_menu_kb, profile_kb, games_kb,
    play_kb, cancel_kb, back_kb, profile_back_kb, promo_cancel_kb,
    roulette_bet_kb, roulette_amount_kb, roulette_cancel_kb,
    history_kb, top_kb, refs_kb, main_reply_kb,
    predict_menu_kb, predict_amount_kb, predict_cancel_kb,
    basket_predict_kb, basket_amount_kb,
    football_predict_kb, football_amount_kb,
    gifts_menu_kb, gift_cancel_kb,
    duels_menu_kb, duel_cancel_kb,
    basket_cancel_kb, football_cancel_kb,
    help_kb, HELP_PAGES,
    vip_menu_kb, vip_confirm_kb, duel_side_kb
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def admin_only(func):
    """Декоратор: только для админов. Уведомляет о попытках."""
    import functools
    @functools.wraps(func)
    async def wrapper(message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            # Логируем
            logging.warning(
                f"ADMIN-DENIED: user_id={message.from_user.id} "
                f"username=@{message.from_user.username} "
                f"text={message.text!r}"
            )
            # Уведомляем всех админов (кроме того кто пытался)
            for admin_id in ADMIN_IDS:
                if admin_id != message.from_user.id:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⚠️ <b>Попытка админ-команды!</b>\n\n"
                            f"🆔 ID: <code>{message.from_user.id}</code>\n"
                            f"👤 Юзер: @{message.from_user.username or 'без_username'}\n"
                            f"📛 Имя: {message.from_user.full_name}\n"
                            f"<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> Команда: <code>{message.text[:100]}</code>"
                        )
                    except Exception:
                        pass
            return
        return await func(message, *args, **kwargs)
    return wrapper

dp = Dispatcher()

BOT_USERNAME = None

AGREEMENT_TEXT = (
    "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> <b>Добро пожаловать в Casino Bot!</b>\n\n"
    "Это <b>развлекательная игра</b> с виртуальными монетами.\n"
    "Реальные деньги здесь НЕ используются.\n\n"
    "⚠️ <b>Условия использования:</b>\n"
    "• Игра только для развлечения\n"
    "• Монеты не имеют денежной ценности\n"
    "• Вывод средств невозможен\n"
    "• Возраст: 18+\n\n"
    "Нажимая «Принимаю», ты соглашаешься с условиями."
)

MAX_BET = 1_000_000_000_000

GAME_EMOJI = {
    "slots": "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Слоты",
    "dice": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кости",
    "darts": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Дартс",
    "basketball": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскетбол",
    "football": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Футбол",
    "bowling": "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> Боулинг",
    "roulette": "<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> Рулетка",
    "predict": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Прогноз кубик",
    "basket_predict": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Прогноз баскет",
    "football_predict": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Прогноз футбол",
    "duel_win": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль (победа)",
    "duel_lose": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль (проигрыш)",
}


BAD_WORDS = [
    "хуй", "хуе", "хуё", "пизд", "бля", "блят", "бляд",
    "ебал", "ебан", "ебат", "еба", "ебёт", "ебет", "еби",
    "ёб", "ёба", "сука", "суки", "сучар",
    "муд", "мудак", "мудил", "гандон", "гондон",
    "долбо", "долба", "залуп", "манда", "мандав",
    "пидор", "пидар", "пидр", "шлюх", "шлюш",
    "нах", "нахуй", "охуе", "ахуе", "ухуе",
    "выеб", "заеб", "доеб", "отъеб", "съеб",
    "fuck", "bitch", "cunt", "dick",
]


def filter_username(username, user_id):
    if not username:
        return f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Игрок #{user_id % 10000}"
    low = username.lower()
    for bad in BAD_WORDS:
        if bad in low:
            return f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Игрок #{user_id % 10000}"
    return f"@{username}"


GAMES = {
    "slots": {"emoji": "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji>", "name": "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Слоты", "anim": 2.5, "payouts": [
        (1, 1, 10.0, "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> BAR BAR BAR"),
        (2, 21, 0, "😭 Мимо"),
        (22, 22, 5.0, "🍒 Три вишенки"),
        (23, 42, 0, "😭 Мимо"),
        (43, 43, 20.0, "7️⃣ ДЖЕКПОТ!"),
        (44, 63, 0, "😭 Мимо"),
        (64, 64, 10.0, "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> BAR BAR BAR")]},
    "dice": {"emoji": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji>", "name": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кости", "anim": 2.5, "payouts": [
        (1, 3, 0, "😭 Мало"), (4, 5, 2.0, "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Хороший бросок"), (6, 6, 3.0, "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> ШЕСТЁРКА!")]},
    "darts": {"emoji": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji>", "name": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Дартс", "anim": 2.5, "payouts": [
        (1, 3, 0, "😭 Промах"), (4, 5, 2.0, "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> В яблочко"), (6, 6, 3.0, "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> БУЛЛ-АЙ!")]},
    "basketball": {"emoji": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji>", "name": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскетбол", "anim": 2.5, "payouts": [
        (1, 3, 0, "😭 Мимо"), (4, 4, 3.0, "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Забил!"), (5, 5, 5.0, "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> Чистый бросок!")]},
    "football": {"emoji": "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>", "name": "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> Футбол", "anim": 2.5, "payouts": [
        (1, 2, 0, "😭 Мимо ворот"), (3, 4, 1.8, "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> ГОЛ!"), (5, 5, 3.0, "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> Красивый гол!")]},
    "bowling": {"emoji": "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji>", "name": "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> Боулинг", "anim": 2.5, "payouts": [
        (1, 3, 0, "😭 Промах"), (4, 5, 2.0, "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> СТРАЙК!"), (6, 6, 3.0, "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> ДВОЙНОЙ СТРАЙК!")]},
}

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


class CustomBet(StatesGroup):
    waiting_amount = State()

class PromoInput(StatesGroup):
    waiting_code = State()

class RouletteNumber(StatesGroup):
    waiting_number = State()


class PredictNumber(StatesGroup):
    waiting_number = State()

class PredictCustomBet(StatesGroup):
    waiting_amount = State()

class DuelState(StatesGroup):
    waiting_amount = State()

class GiftState(StatesGroup):
    waiting_user = State()
    waiting_amount = State()

class FootballCustomBet(StatesGroup):
    waiting_amount = State()


class BasketCustomBet(StatesGroup):
    waiting_amount = State()


def get_payout(game, value):
    for lo, hi, mult, label in GAMES[game]["payouts"]:
        if lo <= value <= hi:
            return mult, label
    return 0, "?"

def is_admin(user_id):
    return user_id in ADMIN_IDS

def roulette_color(n):
    if n == 0:
        return "green"
    if n in RED_NUMBERS:
        return "red"
    return "black"

def roulette_color_label(n):
    c = roulette_color(n)
    if c == "green":
        return "🟢 Зеро"
    if c == "red":
        return "🔴 Красное"
    return "⚫ Чёрное"

def roulette_num_emoji(n):
    c = roulette_color(n)
    if c == "green":
        return "🟢"
    if c == "red":
        return "🔴"
    return "⚫"


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    print(f"START DEBUG: text={message.text!r}")
    await state.clear()
    await ensure_user(message.from_user.id, message.from_user.username)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("duel_"):
        code = args[1].replace("duel_", "")
        await process_duel_join(message, code)
        return
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            referrer_id = None
        if referrer_id and referrer_id != message.from_user.id:
            ok = await set_referrer(message.from_user.id, referrer_id)
            if ok:
                await update_balance(referrer_id, REFERRAL_BONUS)
                await check_achievements(referrer_id, referrer_id)
                try:
                    await bot.send_message(referrer_id, f"🎉 По твоей ссылке зашёл новый игрок!\n💰 +{REFERRAL_BONUS} монет на баланс.")
                except Exception:
                    pass
    if not await is_agreed(message.from_user.id):
        await message.answer(AGREEMENT_TEXT, reply_markup=agreement_kb())
    else:
        await message.answer(
            f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Привет, {message.from_user.first_name}!\n\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(message.from_user.id):.0f} монет",
            reply_markup=main_reply_kb())
        await message.answer("<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Главное меню:", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "accept_agreement")
async def accept_agreement(cb: CallbackQuery):
    await set_agreed(cb.from_user.id, cb.from_user.username)
    await update_balance(cb.from_user.id, 250)
    await cb.message.edit_text(
        "✅ Соглашение принято!\n\n"
        "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Тебе начислено <b>250 монет</b> на старт!\n\n"
        "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Удачи в игре!",
        reply_markup=main_reply_kb())
    await cb.message.answer("<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Главное меню:", reply_markup=main_menu_kb())
    await cb.answer("Добро пожаловать!")


@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    jp = await get_jackpot()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Главное меню</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji> Джекпот: <b>{jp:.0f}</b>",
        reply_markup=main_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "profile")
async def profile(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Профиль не найден", show_alert=True)
        return
    refs = await get_referrals_count(cb.from_user.id)
    username = filter_username(user["username"], user["user_id"])
    text = (f"<tg-emoji emoji-id='5294079931473477913'>📃</tg-emoji> <b>Профиль</b>\n\n<tg-emoji emoji-id='5841276284155467413'>🔤</tg-emoji> ID: <code>{user['user_id']}</code>\n<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Имя: {username}\n\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{user['balance']:.0f}</b> монет\n"
            f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Ставок: {user['total_bets']}\n"
            f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Побед: {user['total_wins']}\n"
            f"<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Проигрышей: {user['total_loses']}\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Всего поставлено: {user['total_wagered']:.0f}\n\n"
            f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Приглашено друзей: <b>{refs}</b>\n\n"
            f"{await format_achievements(cb.from_user.id)}")
    await cb.message.edit_text(text, reply_markup=profile_kb())
    await cb.answer()


@dp.callback_query(F.data == "my_refs")
async def my_refs(cb: CallbackQuery):
    refs = await get_referrals_list(cb.from_user.id, limit=20)
    if not refs:
        await cb.message.edit_text(
            "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> <b>У тебя пока нет приглашённых</b>\n\n"
            "Отправь друзьям свою ссылку и получай +700 монет за каждого!",
            reply_markup=refs_kb())
        await cb.answer()
        return
    lines = [f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> <b>Твои рефералы ({len(refs)})</b>\n"]
    for r in refs:
        name = filter_username(r["username"], r["user_id"])
        lines.append(f"• {name} — <tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> {r['balance']:.0f}")
    await cb.message.edit_text("\n".join(lines), reply_markup=refs_kb())
    await cb.answer()


@dp.callback_query(F.data == "ref_link")
async def ref_link(cb: CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{cb.from_user.id}"
    refs = await get_referrals_count(cb.from_user.id)
    text = (f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> <b>Твоя реферальная ссылка:</b>\n\n<code>{link}</code>\n\n"
            f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Приглашено: <b>{refs}</b>\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> За каждого друга +<b>{REFERRAL_BONUS}</b> монет\n\n"
            f"Копируй и отправляй друзьям!")
    await cb.message.edit_text(text, reply_markup=profile_kb())
    await cb.answer()




@dp.callback_query(F.data.startswith("top_"))
async def top_page(cb: CallbackQuery):
    if cb.data == "top_noop":
        await cb.answer()
        return
    try:
        page = int(cb.data.split("_")[1])
    except (ValueError, IndexError):
        page = 0
    await render_top(cb, page)


async def render_top(cb: CallbackQuery, page: int):
    per_page = 10
    total_limit = 100
    offset = page * per_page
    if offset >= total_limit:
        offset = total_limit - per_page
        page = (total_limit // per_page) - 1
    players = await get_top_players(per_page, offset)
    if not players:
        await cb.message.edit_text(
            "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Топ игроков пуст</b>\n\nСтань первым!",
            reply_markup=back_kb())
        await cb.answer()
        return
    medals = [
        "🔸",
        "2️⃣",
        "3️⃣",
        "4️⃣",
        "5️⃣",
        "6️⃣",
        "7️⃣",
        "8️⃣",
        "9️⃣",
        "💲"
    ]
    total_pages = total_limit // per_page
    lines = [f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Топ игроков</b> ({page+1}/{total_pages})\n"]
    for i, p in enumerate(players):
        rank = page * per_page + i + 1
        if rank <= 3:
            prefix = medals[rank - 1]
        else:
            prefix = f"{rank}."
        name = filter_username(p["username"], p["user_id"])
        lines.append(f"{prefix} {name} — <b>{p['balance']:.0f}</b>")
    await cb.message.edit_text("\n".join(lines), reply_markup=top_kb(page, total_pages))
    await cb.answer()



async def show_history(cb: CallbackQuery):
    await render_history(cb, 0)



async def history_page(cb: CallbackQuery):
    if cb.data == "hist_noop":
        await cb.answer()
        return
    try:
        page = int(cb.data.split("_")[1])
    except (ValueError, IndexError):
        page = 0
    await render_history(cb, page)



@dp.callback_query(F.data == "bonus")
async def bonus(cb: CallbackQuery):
    uid = cb.from_user.id
    vip_level = await get_vip(uid)
    
    cooldown = VIP_COOLDOWN.get(vip_level, BONUS_COOLDOWN)
    bonus_amount = VIP_BONUS.get(vip_level, BONUS_AMOUNT)
    
    now = int(time.time())
    last = await get_last_bonus(uid)
    delta = now - last
    
    if delta < cooldown:
        left = cooldown - delta
        hours = left // 3600
        mins = (left % 3600) // 60
        if hours > 0:
            wait_str = f"{hours} ч {mins} мин"
        elif mins > 0:
            wait_str = f"{mins} мин"
        else:
            wait_str = f"{left} сек"
        await cb.answer(f"<tg-emoji emoji-id='5399850755337240950'>⏳</tg-emoji> Бонус через {wait_str}", show_alert=True)
        return
    
    await update_balance(uid, bonus_amount)
    await set_last_bonus(uid, now)
    
    vip_name = ""
    if vip_level == 1:
        vip_name = " <tg-emoji emoji-id='6084472459329800521'>🥈</tg-emoji>"
    elif vip_level == 2:
        vip_name = " <tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji>"
    
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Бонус получен!</b>{vip_name}\n\n"
        f"💰 +<b>{bonus_amount}</b> монет\n"
        f"<tg-emoji emoji-id='5334708741545680612'>💼</tg-emoji> Новый баланс: {await get_balance(uid):.0f}",
        reply_markup=back_kb())
    await cb.answer("Бонус начислен!")


@dp.callback_query(F.data == "promo")
async def promo_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "<tg-emoji emoji-id='5208962449989988262'><tg-emoji emoji-id='5208962449989988262'>🎟</tg-emoji>️</tg-emoji> <b>Введи промокод:</b>\n\nОтправь его следующим сообщением.",
        reply_markup=promo_cancel_kb())
    await state.set_state(PromoInput.waiting_code)
    await cb.answer()


@dp.message(PromoInput.waiting_code)
async def promo_apply(message: Message, state: FSMContext = None):
    code = message.text.strip()
    try:
        success = await use_promo(code.lower(), message.from_user.id)
        if success:
            await message.answer("✅ Промокод активирован!")
        else:
            await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Неверный код или он уже использован.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    if state:
        await state.clear()

@dp.callback_query(F.data == "play")
async def play_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Выбери игру:</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет",
        reply_markup=games_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("game_"))
async def choose_bet(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    game = cb.data.split("_", 1)[1]
    if game not in GAMES:
        await cb.answer("Игра не найдена", show_alert=True)
        return
    g = GAMES[game]
    last_bet = await get_last_bet(cb.from_user.id)
    await cb.message.edit_text(
        f"{GAME_EMOJI.get(game, g['name'])}\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n\nВыбери ставку:",
        reply_markup=play_kb(game, last_bet))
    await cb.answer()


async def run_game(cb_or_msg, game, bet, chat_id):
    user_id = cb_or_msg.from_user.id
    bal = await get_balance(user_id)
    if bet < 1:
        text = "Минимальная ставка — 1 монета"
        if isinstance(cb_or_msg, CallbackQuery):
            await cb_or_msg.answer(text, show_alert=True)
        else:
            await cb_or_msg.answer(text)
        return
    if bet > MAX_BET:
        text = f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Максимум {MAX_BET:,} монет".replace(",", " ")
        if isinstance(cb_or_msg, CallbackQuery):
            await cb_or_msg.answer(text, show_alert=True)
        else:
            await cb_or_msg.answer(text)
        return
    if bal < bet:
        text = f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Недостаточно монет. Баланс: {bal:.0f}"
        if isinstance(cb_or_msg, CallbackQuery):
            await cb_or_msg.answer(text, show_alert=True)
        else:
            await cb_or_msg.answer(text)
        return
    if isinstance(cb_or_msg, CallbackQuery):
        await cb_or_msg.answer()
    await update_balance(user_id, -bet)
    await set_last_bet(user_id, bet)
    g = GAMES[game]
    dice_msg = await bot.send_dice(chat_id=chat_id, emoji=g["emoji"])
    value = dice_msg.dice.value
    await asyncio.sleep(g["anim"])
    mult, label = get_payout(game, value)
    win = int(bet * mult)
    if win > 0:
        await update_balance(user_id, win)
    await add_bet_stats(user_id, bet, win)
    await add_history(user_id, game, bet, value, win)
    await check_achievements(user_id, chat_id)
    new_bal = await get_balance(user_id)

    # Особые сообщения для баскетбола
    if game == "basketball":
        if value == 5:
            label = "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> Чистый бросок! Идеально!"
        elif value == 4:
            label = "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Гол! Мяч в сетке!"
        elif value == 3:
            label = "<tg-emoji emoji-id='5451927229506268442'>🔔</tg-emoji> Эх, мяч покрутился на дужке и вылетел!"
        else:
            label = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо кольца!"

    # Особые сообщения для футбола
    if game == "football":
        if value == 5:
            label = "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> Красивый гол в девятку!"
        elif value in (3, 4):
            label = "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> ГОЛ! Мяч в воротах!"
        else:
            label = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо ворот!"

    # Особые сообщения для костей
    if game == "dice":
        if value == 6:
            label = "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> ШЕСТЁРКА!"
        elif value == 5:
            label = "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Пятёрка!"
        elif value == 4:
            label = "😊 Четвёрка"
        else:
            label = "😭 Мало"

    # Особые сообщения для дартса
    if game == "darts":
        if value == 6:
            label = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> БУЛЛ-АЙ! В яблочко!"
        elif value == 5:
            label = "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Почти в центр!"
        elif value == 4:
            label = "😊 Хороший бросок"
        else:
            label = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Промах"

    # Особые сообщения для боулинга
    if game == "bowling":
        if value == 6:
            label = "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> ДВОЙНОЙ СТРАЙК!"
        elif value == 5:
            label = "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> СТРАЙК!"
        elif value == 4:
            label = "😊 Почти страйк"
        else:
            label = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Промах"

    # Начисление джекпота (1% от ставки + возможный срыв)
    if mult < 10:
        await process_jackpot(user_id, bet, win, mult, chat_id)

    if win > 0:
        net = win - bet
        sign_str = "+" if net >= 0 else ""
        text = (f"{GAME_EMOJI.get(game, g['name'])}\n<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Результат: <b>{value}</b>\n{label}\n\n"
                f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Выигрыш: <b>{sign_str}{net} монет</b> (x{mult})\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    else:
        text = (f"{GAME_EMOJI.get(game, g['name'])}\n<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Результат: <b>{value}</b>\n{label}\n\n"
                f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Проигрыш: <b>-{bet} монет</b>\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=play_kb(game, bet))


@dp.callback_query(F.data.startswith("play_"))
async def do_play(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) != 3:
        await cb.answer("Ошибка", show_alert=True)
        return
    _, game, bet_str = parts
    if game not in GAMES:
        await cb.answer("Игра не найдена", show_alert=True)
        return
    try:
        bet = int(bet_str)
    except ValueError:
        await cb.answer("Ошибка ставки", show_alert=True)
        return
    await run_game(cb, game, bet, cb.message.chat.id)


@dp.callback_query(F.data.startswith("custombet_"))
async def custom_bet_start(cb: CallbackQuery, state: FSMContext):
    game = cb.data.split("_", 1)[1]
    if game not in GAMES:
        await cb.answer("Игра не найдена", show_alert=True)
        return
    await state.update_data(game=game)
    await cb.message.edit_text(
        f"{GAMES[game]['name']}\n\n✏️ Введи сумму ставки числом (например: 250):",
        reply_markup=cancel_kb())
    await state.set_state(CustomBet.waiting_amount)
    await cb.answer()


@dp.message(CustomBet.waiting_amount)
async def custom_bet_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    game = data.get("game")
    try:
        bet = int(message.text.strip())
        if bet < 1:
            raise ValueError
        if bet > MAX_BET:
            await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Максимум {MAX_BET:,} монет".replace(",", " "))
            return
    except (ValueError, AttributeError, OverflowError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи целое число больше 0:")
        return
    await state.clear()
    await run_game(message, game, bet, message.chat.id)


@dp.callback_query(F.data == "roulette")
async def roulette_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> <b>Рулетка</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n\n"
        f"Выбери тип ставки:\n🔴 Красное / ⚫ Чёрное — x2\n🟢 Зеро — x14\n<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Точное число — x36",
        reply_markup=roulette_bet_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("roul_color_"))
async def roulette_color_choose(cb: CallbackQuery):
    color = cb.data.replace("roul_color_", "")
    if color not in ("red", "black", "green"):
        await cb.answer("Ошибка", show_alert=True)
        return
    names = {"red": "🔴 Красное", "black": "⚫ Чёрное", "green": "🟢 Зеро"}
    last_bet = await get_last_bet(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> <b>Рулетка — {names[color]}</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f}\n\nВыбери сумму:",
        reply_markup=roulette_amount_kb(color, last_bet=last_bet))
    await cb.answer()


@dp.callback_query(F.data == "roul_number")
async def roulette_number_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> <b>Ставка на точное число</b>\n\nВведи число от <b>0 до 36</b>:",
        reply_markup=roulette_cancel_kb())
    await state.set_state(RouletteNumber.waiting_number)
    await cb.answer()


@dp.message(RouletteNumber.waiting_number)
async def roulette_number_set(message: Message, state: FSMContext):
    try:
        num = int(message.text.strip())
        if num < 0 or num > 36:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число от 0 до 36:")
        return
    await state.clear()
    last_bet = await get_last_bet(message.from_user.id)
    await message.answer(
        f"<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Ты выбрал число <b>{num}</b>\n\nВыбери сумму:",
        reply_markup=roulette_amount_kb("number", str(num), last_bet=last_bet))


@dp.callback_query(F.data.startswith("roulbet_"))
async def roulette_play(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 3:
        await cb.answer("Ошибка", show_alert=True)
        return
    bet_type = parts[1]
    if bet_type == "number":
        if len(parts) != 4:
            await cb.answer("Ошибка", show_alert=True)
            return
        try:
            chosen_number = int(parts[2])
            bet = int(parts[3])
        except ValueError:
            await cb.answer("Ошибка ставки", show_alert=True)
            return
    else:
        if len(parts) != 3:
            await cb.answer("Ошибка", show_alert=True)
            return
        chosen_number = None
        try:
            bet = int(parts[2])
        except ValueError:
            await cb.answer("Ошибка ставки", show_alert=True)
            return
    uid = cb.from_user.id
    bal = await get_balance(uid)
    if bet < 1:
        await cb.answer("Минимальная ставка — 1 монета", show_alert=True)
        return
    if bet > MAX_BET:
        await cb.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Максимум {MAX_BET:,} монет".replace(",", " "), show_alert=True)
        return
    if bal < bet:
        await cb.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Недостаточно монет. Баланс: {bal:.0f}", show_alert=True)
        return
    await cb.answer()
    await update_balance(uid, -bet)
    await set_last_bet(uid, bet)

    result = random.randint(0, 36)
    color = roulette_color(result)
    color_label = roulette_color_label(result)
    result_emoji = roulette_num_emoji(result)

    def make_row(nums):
        chunks = []
        for i, n in enumerate(nums):
            e = roulette_num_emoji(n)
            t = e + str(n)
            if i == 2:
                chunks.append("[ " + t + " ]")
            else:
                chunks.append(" " + t + " ")
        return "".join(chunks)

    spin_msg = await bot.send_message(
        chat_id=cb.message.chat.id,
        text="🎡 <b>Крутим рулетку...</b>\n\n" + make_row([0, 0, 0, 0, 0]) + "\n              ⬆️")

    for _ in range(5):
        await asyncio.sleep(0.3)
        nums = [random.randint(0, 36) for _ in range(5)]
        try:
            await spin_msg.edit_text("🎡 <b>Крутим рулетку...</b>\n\n" + make_row(nums) + "\n              ⬆️")
        except Exception:
            pass

    for _ in range(4):
        await asyncio.sleep(0.5)
        nums = [random.randint(0, 36) for _ in range(5)]
        try:
            await spin_msg.edit_text("🎡 <b>Крутим рулетку...</b>\n\n" + make_row(nums) + "\n              ⬆️")
        except Exception:
            pass

    for _ in range(3):
        await asyncio.sleep(0.8)
        nums = [random.randint(0, 36) for _ in range(5)]
        nums[2] = random.randint(max(0, result - 2), min(36, result + 2))
        try:
            await spin_msg.edit_text("🎡 <b>Крутим рулетку...</b>\n\n" + make_row(nums) + "\n              ⬆️")
        except Exception:
            pass

    await asyncio.sleep(0.9)
    nums = [random.randint(0, 36) for _ in range(5)]
    nums[2] = result
    try:
        await spin_msg.edit_text("<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Останавливается...</b>\n\n" + make_row(nums) + "\n              ⬇️")
    except Exception:
        pass
    await asyncio.sleep(1.2)

    win = 0
    mult = 0
    if bet_type == "red" and color == "red":
        mult = 2
    elif bet_type == "black" and color == "black":
        mult = 2
    elif bet_type == "green" and color == "green":
        mult = 14
    elif bet_type == "number" and chosen_number == result:
        mult = 36
    if mult > 0:
        win = bet * mult
        await update_balance(uid, win)
    await add_bet_stats(uid, bet, win)
    await add_history(uid, "roulette", bet, result, win)
    await check_achievements(uid, cb.message.chat.id)
    new_bal = await get_balance(uid)

    if bet_type == "red":
        choice_label = "🔴 Красное"
    elif bet_type == "black":
        choice_label = "⚫ Чёрное"
    elif bet_type == "green":
        choice_label = "🟢 Зеро"
    else:
        choice_label = f"<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Число {chosen_number}"

    if mult < 10:
        await process_jackpot(uid, bet, win, mult, cb.message.chat.id)

    if win > 0:
        net = win - bet
        sign_str = "+" if net >= 0 else ""
        text = (f"<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> <b>Выпало:</b> {result_emoji} <b>{result}</b> {color_label}\n\n"
                f"Твоя ставка: {choice_label}\n\n"
                f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Выигрыш: <b>{sign_str}{net} монет</b> (x{mult})\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    else:
        text = (f"<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> <b>Выпало:</b> {result_emoji} <b>{result}</b> {color_label}\n\n"
                f"Твоя ставка: {choice_label}\n\n"
                f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Проигрыш: <b>-{bet} монет</b>\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    await spin_msg.edit_text(text, reply_markup=roulette_bet_kb())


@dp.message(Command("addpromo"))
async def add_promo_cmd(message: Message):
    args = message.text.split()
    if len(args) != 4:
        await message.answer("Формат: <code>/addpromo КОД СУММА КОЛ-ВО</code>\nПример: <code>/addpromo NEWYEAR 500 10</code>")
        return
    _, code, amount_s, uses_s = args
    try:
        amount = float(amount_s)
        uses = int(uses_s)
    except ValueError:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Сумма и количество должны быть числами")
        return
    ok = await create_promo(code, amount, uses, message.from_user.id)
    if ok:
        await message.answer(f"✅ Промокод создан:\n\n<tg-emoji emoji-id='5208962449989988262'>🎟</tg-emoji> Код: <code>{code.upper()}</code>\n💰 Сумма: {amount:.0f}\n👥 Использований: {uses}")
    else:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Такой промокод уже существует")


@dp.message(Command("delpromo"))
async def del_promo_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: <code>/delpromo КОД</code>")
        return
    ok = await delete_promo(args[1])
    if ok:
        await message.answer(f"✅ Промокод <code>{args[1].upper()}</code> удалён")
    else:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Промокод не найден")


@dp.message(Command("promos"))
async def list_promos_cmd(message: Message):
    promos = await list_promos()
    if not promos:
        await message.answer("Промокодов нет")
        return
    text = "<tg-emoji emoji-id='5208962449989988262'><tg-emoji emoji-id='5208962449989988262'>🎟</tg-emoji>️</tg-emoji> <b>Активные промокоды:</b>\n\n"
    for p in promos:
        text += f"• <code>{p['code']}</code> — {p['amount']:.0f} монет, осталось {p['uses_left']}\n"
    await message.answer(text)


async def admin_help(message: Message):
    await message.answer("<tg-emoji emoji-id='5192881946404874629'>🔧</tg-emoji> <b>Админ-команды:</b>\n\n"
                         "<code>/addpromo КОД СУММА КОЛ-ВО</code> — создать промокод\n"
                         "<code>/delpromo КОД</code> — удалить промокод\n"
                         "<code>/promos</code> — список промокодов")




class RouletteCustomBet(StatesGroup):
    waiting_amount = State()


@dp.callback_query(F.data.startswith("roulcustom_"))
async def roulette_custom_start(cb: CallbackQuery, state: FSMContext):
    suffix = cb.data.replace("roulcustom_", "")
    await state.update_data(roul_suffix=suffix)
    await cb.message.edit_text(
        "✏️ Введи сумму ставки числом:",
        reply_markup=roulette_cancel_kb())
    await state.set_state(RouletteCustomBet.waiting_amount)
    await cb.answer()


@dp.message(RouletteCustomBet.waiting_amount)
async def roulette_custom_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    suffix = data.get("roul_suffix")
    try:
        bet = int(message.text.strip())
        if bet < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 0:")
        return
    await state.clear()
    parts = suffix.split("_")
    if parts[0] == "number":
        data_str = "roulbet_number_" + parts[1] + "_" + str(bet)
    else:
        data_str = "roulbet_" + suffix + "_" + str(bet)
    class FakeCB:
        def __init__(self, msg, user, data):
            self.message = msg
            self.from_user = user
            self.data = data
        async def answer(self, *a, **k):
            pass
    fake = FakeCB(message, message.from_user, data_str)
    await roulette_play(fake)


@dp.callback_query(F.data == "predict")
async def predict_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Прогноз на кубик</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n\n"
        f"Выбери на что ставишь:\n"
        f"<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Чёт / Нечет — x1.9\n"
        f"⬆️ Больше 3 / Меньше 4 — x1.9\n"
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Точное число — x5",
        reply_markup=predict_menu_kb())
    await cb.answer()


@dp.callback_query(F.data.in_({"pred_even", "pred_odd", "pred_high", "pred_low"}))
async def predict_choose_amount(cb: CallbackQuery):
    ptype = cb.data.replace("pred_", "")
    names = {"even": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Чёт", "odd": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Нечет", "high": "⬆️ Больше 3", "low": "⬇️ Меньше 4"}
    last_bet = await get_last_bet(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Прогноз — {names.get(ptype, ptype)}</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f}\n\n"
        f"Выбери сумму:",
        reply_markup=predict_amount_kb(ptype, last_bet=last_bet))
    await cb.answer()


@dp.callback_query(F.data == "pred_exact")
async def predict_exact_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Прогноз на точное число</b>\n\nВведи число от <b>1 до 6</b>:",
        reply_markup=predict_cancel_kb())
    await state.set_state(PredictNumber.waiting_number)
    await cb.answer()


@dp.message(PredictNumber.waiting_number)
async def predict_exact_number(message: Message, state: FSMContext):
    try:
        num = int(message.text.strip())
        if num < 1 or num > 6:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число от 1 до 6:")
        return
    await state.clear()
    last_bet = await get_last_bet(message.from_user.id)
    await message.answer(
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Ты выбрал число <b>{num}</b>\n\nВыбери сумму:",
        reply_markup=predict_amount_kb("exact", str(num), last_bet=last_bet))


@dp.callback_query(F.data.startswith("predbet_"))
async def predict_play(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 3:
        await cb.answer("Ошибка", show_alert=True)
        return
    ptype = parts[1]
    if ptype == "exact":
        if len(parts) != 4:
            await cb.answer("Ошибка", show_alert=True)
            return
        try:
            chosen = int(parts[2])
            bet = int(parts[3])
        except ValueError:
            await cb.answer("Ошибка", show_alert=True)
            return
    else:
        if len(parts) != 3:
            await cb.answer("Ошибка", show_alert=True)
            return
        chosen = None
        try:
            bet = int(parts[2])
        except ValueError:
            await cb.answer("Ошибка", show_alert=True)
            return
    uid = cb.from_user.id
    bal = await get_balance(uid)
    if bet < 1 or bal < bet:
        await cb.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Баланс: {bal:.0f}", show_alert=True)
        return
    await cb.answer()
    await update_balance(uid, -bet)
    await set_last_bet(uid, bet)
    dice_msg = await bot.send_dice(chat_id=cb.message.chat.id, emoji="<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji>")
    value = dice_msg.dice.value
    await asyncio.sleep(2.5)
    win = 0
    mult = 0
    if ptype == "even" and value % 2 == 0:
        mult = 1.9
    elif ptype == "odd" and value % 2 == 1:
        mult = 1.9
    elif ptype == "high" and value >= 4:
        mult = 1.9
    elif ptype == "low" and value <= 3:
        mult = 1.9
    elif ptype == "exact" and value == chosen:
        mult = 5
    if mult > 0:
        win = int(bet * mult)
        await update_balance(uid, win)
    await add_bet_stats(uid, bet, win)
    await add_history(uid, "predict", bet, value, win)
    new_bal = await get_balance(uid)
    labels = {"even": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Чёт", "odd": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Нечет", "high": "⬆️ Больше 3", "low": "⬇️ Меньше 4", "exact": f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Число {chosen}"}
    choice = labels.get(ptype, ptype)
    if win > 0:
        net = win - bet
        sign_str = "+" if net >= 0 else ""
        text = f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Выпало: {value}</b>\n\nТвой прогноз: {choice}\n\n<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Выигрыш: <b>{sign_str}{net} монет</b> (x{mult})\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>"
    else:
        text = f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Выпало: {value}</b>\n\nТвой прогноз: {choice}\n\n😭 Проигрыш: <b>-{bet} монет</b>\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>"
    await bot.send_message(chat_id=cb.message.chat.id, text=text, reply_markup=predict_menu_kb())


@dp.callback_query(F.data == "basket_predict")
async def basket_predict_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> <b>Прогноз на баскетбол</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n\n"
        f"Выбери исход:\n"
        f"<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Забьёт (4-5) — x2.5\n"
        f"<tg-emoji emoji-id='5451927229506268442'>🔔</tg-emoji> Застрянет на дужке (3) — x7\n"
        f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не забьёт (1-2) — x2",
        reply_markup=basket_predict_kb())
    await cb.answer()


@dp.callback_query(F.data.in_({"bpred_hit", "bpred_stuck", "bpred_miss"}))
async def basket_predict_choose(cb: CallbackQuery):
    ptype = cb.data.replace("bpred_", "")
    names = {"hit": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Забьёт", "stuck": "<tg-emoji emoji-id='5451927229506268442'>🔔</tg-emoji> Застрянет", "miss": "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не забьёт"}
    last_bet = await get_last_bet(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> <b>Прогноз — {names.get(ptype, ptype)}</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f}\n\n"
        f"Выбери сумму:",
        reply_markup=basket_amount_kb(ptype, last_bet))
    await cb.answer()


@dp.callback_query(F.data.startswith("bpredcustom_"))
async def basket_custom_start(cb: CallbackQuery, state: FSMContext):
    ptype = cb.data.replace("bpredcustom_", "")
    await state.update_data(bpred_type=ptype)
    await cb.message.edit_text(
        "✏️ Введи сумму ставки числом:",
        reply_markup=basket_cancel_kb())
    await state.set_state(BasketCustomBet.waiting_amount)
    await cb.answer()


@dp.message(BasketCustomBet.waiting_amount)
async def basket_custom_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    ptype = data.get("bpred_type")
    try:
        bet = int(message.text.strip())
        if bet < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 0:")
        return
    await state.clear()

    class FakeCB:
        def __init__(self, msg, user, data):
            self.message = msg
            self.from_user = user
            self.data = data
        async def answer(self, *a, **k):
            pass

    fake = FakeCB(message, message.from_user, f"bpredbet_{ptype}_{bet}")
    await basket_predict_play(fake)


@dp.callback_query(F.data.startswith("bpredbet_"))
async def basket_predict_play(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) != 3:
        await cb.answer("Ошибка", show_alert=True)
        return
    ptype = parts[1]
    try:
        bet = int(parts[2])
    except ValueError:
        await cb.answer("Ошибка ставки", show_alert=True)
        return

    uid = cb.from_user.id
    bal = await get_balance(uid)
    if bet < 1:
        await cb.answer("Минимальная ставка — 1 монета", show_alert=True)
        return
    if bal < bet:
        await cb.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Баланс: {bal:.0f}", show_alert=True)
        return
    await cb.answer()
    await update_balance(uid, -bet)
    await set_last_bet(uid, bet)

    dice_msg = await bot.send_dice(chat_id=cb.message.chat.id, emoji="<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji>")
    value = dice_msg.dice.value
    await asyncio.sleep(2.5)

    win = 0
    mult = 0
    if ptype == "hit" and value in (4, 5):
        mult = 2.5
    elif ptype == "stuck" and value == 3:
        mult = 7
    elif ptype == "miss" and value in (1, 2):
        mult = 2

    if mult > 0:
        win = int(bet * mult)
        await update_balance(uid, win)

    await add_bet_stats(uid, bet, win)
    await add_history(uid, "basket_predict", bet, value, win)
    new_bal = await get_balance(uid)

    names = {"hit": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Забьёт", "stuck": "<tg-emoji emoji-id='5451927229506268442'>🔔</tg-emoji> Застрянет", "miss": "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не забьёт"}
    choice = names.get(ptype, ptype)

    if value == 5:
        result_text = "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> Чистый бросок!"
    elif value == 4:
        result_text = "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Гол! Мяч в сетке!"
    elif value == 3:
        result_text = "<tg-emoji emoji-id='5451927229506268442'>🔔</tg-emoji> Мяч покрутился на дужке и вылетел!"
    else:
        result_text = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо кольца!"

    if win > 0:
        net = win - bet
        sign_str = "+" if net >= 0 else ""
        text = (f"<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> <b>Результат: {value}</b>\n{result_text}\n\n"
                f"Твой прогноз: {choice}\n\n"
                f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Выигрыш: <b>{sign_str}{net} монет</b> (x{mult})\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    else:
        text = (f"<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> <b>Результат: {value}</b>\n{result_text}\n\n"
                f"Твой прогноз: {choice}\n\n"
                f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Проигрыш: <b>-{bet} монет</b>\n"
                f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>")
    await bot.send_message(chat_id=cb.message.chat.id, text=text, reply_markup=basket_predict_kb())






@dp.callback_query(F.data == "football_predict")
async def football_predict_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> <b>Прогноз на футбол</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f} монет\n\n"
        f"Выбери исход:\n"
        f"<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> Гол (3-5) — x2\n"
        f"🥅 Штанга (2) — x7\n"
        f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо (1) — x2.5",
        reply_markup=football_predict_kb())
    await cb.answer()


@dp.callback_query(F.data.in_({"fpred_goal", "fpred_post", "fpred_miss"}))
async def football_predict_choose(cb: CallbackQuery):
    ptype = cb.data.replace("fpred_", "")
    names = {"goal": "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> Гол", "post": "🥅 Штанга", "miss": "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо"}
    last_bet = await get_last_bet(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> <b>Прогноз — {names.get(ptype, ptype)}</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(cb.from_user.id):.0f}\n\n"
        f"Выбери сумму:",
        reply_markup=football_amount_kb(ptype, last_bet))
    await cb.answer()


@dp.callback_query(F.data.startswith("fpredcustom_"))
async def football_custom_start(cb: CallbackQuery, state: FSMContext):
    ptype = cb.data.replace("fpredcustom_", "")
    await state.update_data(fpred_type=ptype)
    await cb.message.edit_text(
        "✏️ Введи сумму ставки числом:",
        reply_markup=football_cancel_kb())
    await state.set_state(FootballCustomBet.waiting_amount)
    await cb.answer()


@dp.message(FootballCustomBet.waiting_amount)
async def football_custom_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    ptype = data.get("fpred_type")
    try:
        bet = int(message.text.strip())
        if bet < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 0:")
        return
    await state.clear()
    class FakeCB:
        def __init__(self, msg, user, data):
            self.message = msg
            self.from_user = user
            self.data = data
        async def answer(self, *a, **k):
            pass
    fake = FakeCB(message, message.from_user, f"fpredbet_{ptype}_{bet}")
    await football_predict_play(fake)


@dp.callback_query(F.data.startswith("fpredbet_"))
async def football_predict_play(cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) != 3:
        await cb.answer("Ошибка", show_alert=True)
        return
    ptype = parts[1]
    try:
        bet = int(parts[2])
    except ValueError:
        await cb.answer("Ошибка ставки", show_alert=True)
        return
    uid = cb.from_user.id
    bal = await get_balance(uid)
    if bet < 1 or bal < bet:
        await cb.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Баланс: {bal:.0f}", show_alert=True)
        return
    await cb.answer()
    await update_balance(uid, -bet)
    await set_last_bet(uid, bet)
    dice_msg = await bot.send_dice(chat_id=cb.message.chat.id, emoji="<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>")
    value = dice_msg.dice.value
    await asyncio.sleep(2.5)
    win = 0
    mult = 0
    if ptype == "goal" and value in (3, 4, 5):
        mult = 2
    elif ptype == "post" and value == 2:
        mult = 7
    elif ptype == "miss" and value == 1:
        mult = 2.5
    if mult > 0:
        win = int(bet * mult)
        await update_balance(uid, win)
    await add_bet_stats(uid, bet, win)
    await add_history(uid, "football_predict", bet, value, win)
    new_bal = await get_balance(uid)
    names = {"goal": "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> Гол", "post": "🥅 Штанга", "miss": "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо"}
    choice = names.get(ptype, ptype)
    if value == 1:
        result_text = "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Мимо ворот!"
    elif value == 2:
        result_text = "🥅 Мяч в штанге!"
    else:
        result_text = "<tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji> ГОЛ! Мяч в сетке!"
    if win > 0:
        net = win - bet
        sign_str = "+" if net >= 0 else ""
        text = f"<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> <b>Результат: {value}</b>\n{result_text}\n\nТвой прогноз: {choice}\n\n<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Выигрыш: <b>{sign_str}{net} монет</b> (x{mult})\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>"
    else:
        text = f"<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> <b>Результат: {value}</b>\n{result_text}\n\nТвой прогноз: {choice}\n\n😭 Проигрыш: <b>-{bet} монет</b>\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{new_bal:.0f}</b>"
    await bot.send_message(chat_id=cb.message.chat.id, text=text, reply_markup=football_predict_kb())


@dp.message(F.text == "🏠 Меню")
async def reply_menu(message: Message, state: FSMContext):
    await state.clear()
    await ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Главное меню</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(message.from_user.id):.0f} монет",
        reply_markup=main_menu_kb())




@dp.callback_query(F.data == "gifts")
async def gifts_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    bal = await get_balance(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Подарки</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Твой баланс: <b>{bal:.0f}</b> монет\n\n"
        f"Выбери действие:",
        reply_markup=gifts_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "gift_send")
async def gift_send_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Подарить монеты</b>\n\n"
        "Отправь <b>ID пользователя</b>, которому хочешь подарить.\n\n"
        "<tg-emoji emoji-id='5285133879668137515'>💡</tg-emoji> Узнать свой ID можно в профиле.",
        reply_markup=gift_cancel_kb())
    await state.set_state(GiftState.waiting_user)
    await cb.answer()


@dp.message(GiftState.waiting_user)
async def gift_send_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи числовой ID:")
        return
    if uid == message.from_user.id:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Нельзя подарить монеты самому себе.")
        return
    user = await find_user_by_id(uid)
    if not user:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Пользователь с таким ID не найден в боте.")
        return
    await state.update_data(receiver_id=uid, receiver_name=user["username"])
    await message.answer(
        f"👤 Получатель: <b>@{user['username'] or uid}</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Сколько монет подарить?",
        reply_markup=gift_cancel_kb())
    await state.set_state(GiftState.waiting_amount)


@dp.message(GiftState.waiting_amount)
async def gift_send_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    receiver_id = data.get("receiver_id")
    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 0:")
        return
    bal = await get_balance(message.from_user.id)
    if bal < amount:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Недостаточно монет. Баланс: {bal:.0f}")
        await state.clear()
        return
    await update_balance(message.from_user.id, -amount)
    await update_balance(receiver_id, amount)
    await add_gift(message.from_user.id, receiver_id, amount)
    await state.clear()
    await message.answer(
        f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Подарок отправлен!</b>\n\n"
        f"💰 Сумма: <b>{amount}</b> монет\n"
        f"👤 Получатель: <code>{receiver_id}</code>",
        reply_markup=gifts_menu_kb())
    try:
        sender = await get_user(message.from_user.id)
        sender_name = sender["username"] if sender and sender["username"] else f"ID {message.from_user.id}"
        await bot.send_message(
            receiver_id,
            f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Тебе подарок!</b>\n\n"
            f"💰 <b>+{amount}</b> монет\n"
            f"👤 От: @{sender_name}" if sender_name and not sender_name.startswith("ID") else f"👤 От: {sender_name}"
        )
    except Exception:
        pass


@dp.callback_query(F.data == "gift_received")
async def gift_received(cb: CallbackQuery):
    gifts = await get_gifts_received(cb.from_user.id, limit=10)
    if not gifts:
        await cb.message.edit_text(
            "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Полученные подарки пусты</b>",
            reply_markup=gifts_menu_kb())
        await cb.answer()
        return
    lines = ["<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Последние полученные:</b>\n"]
    for g in gifts:
        name = g["sender_name"] or f"ID {g['sender_id']}"
        lines.append(f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>+{g['amount']:.0f}</b> от @{name}")
    await cb.message.edit_text("\n".join(lines), reply_markup=gifts_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "gift_sent")
async def gift_sent(cb: CallbackQuery):
    gifts = await get_gifts_sent(cb.from_user.id, limit=10)
    if not gifts:
        await cb.message.edit_text(
            "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Отправленных подарков нет</b>",
            reply_markup=gifts_menu_kb())
        await cb.answer()
        return
    lines = ["<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Последние отправленные:</b>\n"]
    for g in gifts:
        name = g["receiver_name"] or f"ID {g['receiver_id']}"
        lines.append(f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>-{g['amount']:.0f}</b> для @{name}")
    await cb.message.edit_text("\n".join(lines), reply_markup=gifts_menu_kb())
    await cb.answer()




async def process_jackpot(user_id, bet, win, mult, chat_id):
    # 3% от ставки идёт в джекпот
    await add_to_jackpot(bet * 0.03)
    # Срыв джекпота: только при x10+ и шансе 1 из 100
    if mult >= 10 and win > 0:
        if random.randint(1, 100) != 1:
            return 0
        jackpot = await claim_jackpot()
        await update_balance(user_id, jackpot)
        await unlock_achievement(user_id, "jackpot")
        msg = (
            "\U0001F389\U0001F389\U0001F389 <b>ДЖЕКПОТ СОРВАН!</b> \U0001F389\U0001F389\U0001F389\n\n"
            "\U0001F4B0 Ты выиграл <b>+" + str(int(jackpot)) + "</b> монет!\n"
            "\U0001F3C6 Множитель: <b>x" + str(mult) + "</b>\n"
            "\u2699\ufe0f Новый джекпот: 1000 монет\n\n"
            "\U0001F340 Тебе повезло \u2014 шанс был 1 из 100!"
        )
        try:
            await bot.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass
        return jackpot
    return 0




async def check_achievements(user_id, chat_id=None):
    """Проверяет и открывает достижения. Уведомляет в чат."""
    unlocked = []
    user = await get_user(user_id)
    if not user:
        return
    bal = user["balance"]
    bets = user["total_bets"]
    wins = user["total_wins"]
    refs = await get_referrals_count(user_id)

    checks = [
        ("first_bet", bets >= 1),
        ("wins_10", wins >= 10),
        ("wins_100", wins >= 100),
        ("bets_100", bets >= 100),
        ("bets_1000", bets >= 1000),
        ("rich_10k", bal >= 10000),
        ("rich_1m", bal >= 1000000),
        ("referral_1", refs >= 1),
        ("referral_10", refs >= 10),
    ]
    for ach_id, condition in checks:
        if condition:
            is_new = await unlock_achievement(user_id, ach_id)
            if is_new:
                unlocked.append(ach_id)

    if unlocked and chat_id:
        ach_dict = {a[0]: a for a in ACHIEVEMENTS}
        lines = ["<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>НОВОЕ ДОСТИЖЕНИЕ!</b>\n"]
        for aid in unlocked:
            e, name, desc = ach_dict[aid][1], ach_dict[aid][2], ach_dict[aid][3]
            lines.append(f"{e} <b>{name}</b> \u2014 {desc}")
        try:
            await bot.send_message(chat_id=chat_id, text="\n".join(lines))
        except Exception:
            pass
    return unlocked



async def format_achievements(user_id):
    user_achs = await get_user_achievements(user_id)
    total = len(ACHIEVEMENTS)
    got = len(user_achs)
    lines = [f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Достижения:</b> {got}/{total}\n"]
    for aid, emoji, name, desc in ACHIEVEMENTS:
        if aid in user_achs:
            lines.append(f"{emoji} {name}")
        else:
            lines.append(f"\u26AA {desc}")
    return "\n".join(lines)

@dp.message(F.text == "👤 Профиль")
async def reply_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Профиль не найден")
        return
    refs = await get_referrals_count(message.from_user.id)
    username = filter_username(user["username"], user["user_id"])
    text = (f"<tg-emoji emoji-id='5294079931473477913'>📃</tg-emoji> <b>Профиль</b>\n\n<tg-emoji emoji-id='5841276284155467413'>🔤</tg-emoji> ID: <code>{user['user_id']}</code>\n<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Имя: {username}\n\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{user['balance']:.0f}</b> монет\n"
            f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Ставок: {user['total_bets']}\n"
            f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Побед: {user['total_wins']}\n"
            f"<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Проигрышей: {user['total_loses']}\n"
            f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Всего поставлено: {user['total_wagered']:.0f}\n\n"
            f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Приглашено друзей: <b>{refs}</b>\n\n"
            f"{await format_achievements(message.from_user.id)}")
    await message.answer(text, reply_markup=profile_kb())


@dp.message(F.text == "<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Играть")
async def reply_play(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Выбери игру:</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {await get_balance(message.from_user.id):.0f} монет",
        reply_markup=games_kb())


@dp.message(F.text == "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Топ")




@dp.callback_query(F.data == "predict")



@dp.callback_query(F.data == "duels")
async def duels_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    bal = await get_balance(cb.from_user.id)
    await cb.message.edit_text(
        f"<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> <b>Дуэли</b>\n\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: <b>{bal:.0f}</b> монет\n\n"
        f"Создай дуэль, отправь ссылку другу — и монетка решит, кто заберёт банк!",
        reply_markup=duels_menu_kb())
    await cb.answer()



async def process_duel_join(message: Message, code: str):
    duel = await get_duel(code)
    if not duel:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Дуэль не найдена.")
        return
    if duel["status"] != "waiting":
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Эта дуэль уже неактивна.")
        return
    if duel["creator_id"] == message.from_user.id:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Ты не можешь играть сам с собой!")
        return
    amount = duel["amount"]
    bal = await get_balance(message.from_user.id)
    if bal < amount:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не хватает монет. Нужно {amount:.0f}, у тебя {bal:.0f}.")
        return
    joined = await join_duel(code, message.from_user.id)
    if not joined:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не удалось присоединиться.")
        return
    await update_balance(message.from_user.id, -amount)

    creator_id = duel["creator_id"]
    joiner_id = message.from_user.id

    DUEL = "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji>"
    TOP = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>"
    DART = "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji>"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"

    # 1. Уведомление о старте
    start_text = (
        DUEL + " <b>Соперник найден!</b>\n\n"
        + DOLLAR + f" Ставка: <b>{amount:.0f}</b> монет\n\n"
        + "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Бросаем кубики..."
    )
    try:
        await bot.send_message(creator_id, start_text)
    except Exception:
        pass
    await message.answer(start_text)
    await asyncio.sleep(1.5)

    # 2. Кубики — одинаковые для обоих
    p1_roll = random.randint(1, 6)
    p2_roll = random.randint(1, 6)
    while p1_roll == p2_roll:
        p1_roll = random.randint(1, 6)
        p2_roll = random.randint(1, 6)

    frames = [(random.randint(1, 6), random.randint(1, 6)) for _ in range(9)]

    # Анимация у джойнера
    await animate_cubes(message.chat.id, p1_roll, p2_roll, frames)
    # Анимация у создателя
    try:
        await animate_cubes(creator_id, p1_roll, p2_roll, frames)
    except Exception:
        pass

    await asyncio.sleep(0.8)

    # 3. Кто победил в кубике
    cube_winner = creator_id if p2_roll > p1_roll else joiner_id
    await set_duel_rolls(code, p1_roll, p2_roll, cube_winner)

    # Текст результата
    result_text = (
        TOP + " <b>Кубики брошены!</b>\n\n"
        + DART + f" <b>{p1_roll} : {p2_roll}</b>\n\n"
    )

    if cube_winner == joiner_id:
        await message.answer(
            result_text
            + TOP + " Ты победил в кубике!\n\n"
            + "Выбери сторону:",
            reply_markup=duel_side_kb(code)
        )
        try:
            await bot.send_message(
                creator_id,
                result_text
                + "😢 Противник победил в кубике.\n"
                + "Он выбирает сторону..."
            )
        except Exception:
            pass
    else:
        await message.answer(
            result_text
            + "😢 Противник победил в кубике.\n"
            + "Он выбирает сторону..."
        )
        try:
            await bot.send_message(
                creator_id,
                result_text
                + TOP + " Ты победил в кубике!\n\n"
                + "Выбери сторону:",
                reply_markup=duel_side_kb(code)
            )
        except Exception:
            pass


@dp.callback_query(F.data == "duel_create")
async def duel_create_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> <b>Создание дуэли</b>\n\n"
        "Введи сумму ставки (числом):",
        reply_markup=duel_cancel_kb())
    await state.set_state(DuelState.waiting_amount)
    await cb.answer()



@dp.message(DuelState.waiting_amount)
async def duel_create_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount < 10:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 10:")
        return
    bal = await get_balance(message.from_user.id)
    if bal < amount:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Недостаточно монет. Баланс: {bal:.0f}")
        await state.clear()
        return
    await update_balance(message.from_user.id, -amount)
    code = await create_duel(message.from_user.id, amount)
    await state.clear()
    link = f"https://t.me/{BOT_USERNAME}?start=duel_{code}"
    await message.answer(
        f"<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> <b>Дуэль создана!</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Ставка: <b>{amount}</b> монет\n"
        f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Ссылка для друга:\n<code>{link}</code>\n\n"
        f"3️⃣ Ждём соперника 1 час.\n"
        f"Если никто не зайдёт — ставка вернётся.",
        reply_markup=duels_menu_kb())



@dp.callback_query(F.data == "duel_history")
async def duel_history(cb: CallbackQuery):
    duels = await get_user_duels(cb.from_user.id, limit=10)
    if not duels:
        await cb.message.edit_text(
            "📜 <b>Дуэлей пока нет</b>\n\nСоздай первую!",
            reply_markup=duels_menu_kb())
        await cb.answer()
        return
    
    lines = ["📜 <b>Мои дуэли:</b>\n"]
    for d in duels:
        won = d["winner_id"] == cb.from_user.id
        # Кто opponent
        if d["creator_id"] == cb.from_user.id:
            opp_id = d["opponent_id"]
        else:
            opp_id = d["creator_id"]
        
        opp_user = await get_user(opp_id) if opp_id else None
        opp_name = filter_username(opp_user["username"] if opp_user else None, opp_id) if opp_id else "?"
        
        if won:
            mark = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>"
            result = "Выигрыш"
        else:
            mark = "😢"
            result = "Проигрыш"
        
        lines.append(f"{mark} {result} · {d['amount']:.0f} монет")
        lines.append(f"   🆚 {opp_name}\n")
    
    await cb.message.edit_text("\n".join(lines), reply_markup=duels_menu_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("predcustom_"))
async def predict_custom_start(cb: CallbackQuery, state: FSMContext):
    suffix = cb.data.replace("predcustom_", "")
    await state.update_data(pred_suffix=suffix)
    await cb.message.edit_text(
        "✏️ Введи сумму ставки числом:",
        reply_markup=predict_cancel_kb())
    await state.set_state(PredictCustomBet.waiting_amount)
    await cb.answer()



@dp.message(PredictCustomBet.waiting_amount)
async def predict_custom_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    suffix = data.get("pred_suffix")
    try:
        bet = int(message.text.strip())
        if bet < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Введи число больше 0:")
        return
    await state.clear()
    parts = suffix.split("_")
    if parts[0] == "exact":
        data_str = "predbet_exact_" + parts[1] + "_" + str(bet)
    else:
        data_str = "predbet_" + suffix + "_" + str(bet)

    class FakeCB:
        def __init__(self, msg, user, data):
            self.message = msg
            self.from_user = user
            self.data = data
        async def answer(self, *a, **k):
            pass

    fake = FakeCB(message, message.from_user, data_str)
    await predict_play(fake)

@dp.callback_query(F.data.startswith("allin_"))
async def allin_bet(cb: CallbackQuery):
    rest = cb.data.replace("allin_", "", 1)
    bal = await get_balance(cb.from_user.id)
    bet = int(bal)
    if bet > MAX_BET:
        bet = MAX_BET
    if bet < 1:
        await cb.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Нет монет на балансе", show_alert=True)
        return

    class FakeCB:
        def __init__(self, msg, user, data):
            self.message = msg
            self.from_user = user
            self.data = data
        async def answer(self, *a, **k):
            pass

    if rest.startswith("play_"):
        game = rest.replace("play_", "")
        fake = FakeCB(cb.message, cb.from_user, f"play_{game}_{bet}")
        await do_play(fake)
    elif rest.startswith("predbet_"):
        tail = rest.replace("predbet_", "")
        fake = FakeCB(cb.message, cb.from_user, f"predbet_{tail}_{bet}")
        await predict_play(fake)
    elif rest.startswith("bpredbet_"):
        tail = rest.replace("bpredbet_", "")
        fake = FakeCB(cb.message, cb.from_user, f"bpredbet_{tail}_{bet}")
        await basket_predict_play(fake)
    elif rest.startswith("fpredbet_"):
        tail = rest.replace("fpredbet_", "")
        fake = FakeCB(cb.message, cb.from_user, f"fpredbet_{tail}_{bet}")
        await football_predict_play(fake)
    elif rest.startswith("roulbet_"):
        tail = rest.replace("roulbet_", "")
        fake = FakeCB(cb.message, cb.from_user, f"roulbet_{tail}_{bet}")
        await roulette_play(fake)
    else:
        await cb.answer("Неизвестный тип", show_alert=True)

@dp.callback_query(F.data == "stats")
async def show_stats(cb: CallbackQuery):
    total = await get_total_stats(cb.from_user.id)
    total_bets, total_wins, total_bet_sum, total_win_sum = total
    total_bets = total_bets or 0
    total_wins = total_wins or 0
    total_bet_sum = total_bet_sum or 0
    total_win_sum = total_win_sum or 0

    if total_bets == 0:
        await cb.message.edit_text(
            "<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> <b>Статистика пуста</b>\n\nСыграй первую игру!",
            reply_markup=profile_back_kb())
        await cb.answer()
        return

    total_losses = total_bets - total_wins
    winrate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    net = total_win_sum - total_bet_sum
    net_str = f"+{net:.0f}" if net >= 0 else f"{net:.0f}"

    lines = [
        "<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> <b>Статистика</b>\n",
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Всего ставок: <b>{total_bets}</b>",
        f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Побед: <b>{total_wins}</b> ({winrate:.1f}%)",
        f"<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Проигрышей: <b>{total_losses}</b>",
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Поставлено: <b>{total_bet_sum:.0f}</b>",
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Выиграно: <b>{total_win_sum:.0f}</b>",
        f"<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Чистый итог: <b>{net_str}</b>\n",
        "<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>По играм:</b>\n",
    ]

    game_names = {
        "slots": "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Слоты",
        "dice": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кости",
        "darts": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Дартс",
        "basketball": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскет",
        "football": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Футбол",
        "bowling": "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> Боулинг",
        "roulette": "<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> Рулетка",
        "predict": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Прогноз кубик",
        "basket_predict": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Прогноз баскет",
        "football_predict": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Прогноз футбол",
        "duel_win": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль (победа)",
        "duel_lose": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль (проигрыш)",
    }

    stats = await get_game_stats(cb.from_user.id)
    for game, count, wins, bet_sum, win_sum in stats:
        name = game_names.get(game, game)
        wins = wins or 0
        bet_sum = bet_sum or 0
        win_sum = win_sum or 0
        diff = win_sum - bet_sum
        diff_str = f"+{diff:.0f}" if diff >= 0 else f"{diff:.0f}"
        lines.append(f"{name}: {count} игр, W{wins}/{count} ({diff_str})")

    await cb.message.edit_text("\n".join(lines), reply_markup=profile_back_kb())
    await cb.answer()



@dp.message(F.text == "📊 Статистика")
async def reply_stats(message: Message):
    total = await get_total_stats(message.from_user.id)
    total_bets, total_wins, total_bet_sum, total_win_sum = total
    total_bets = total_bets or 0
    total_wins = total_wins or 0
    total_bet_sum = total_bet_sum or 0
    total_win_sum = total_win_sum or 0

    if total_bets == 0:
        await message.answer("<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> <b>Статистика пуста</b>\n\nСыграй первую игру!",
                             reply_markup=profile_back_kb())
        return

    total_losses = total_bets - total_wins
    winrate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    net = total_win_sum - total_bet_sum
    net_str = f"+{net:.0f}" if net >= 0 else f"{net:.0f}"

    lines = [
        "<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> <b>Статистика</b>\n",
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Всего ставок: <b>{total_bets}</b>",
        f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Побед: <b>{total_wins}</b> ({winrate:.1f}%)",
        f"<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji> Проигрышей: <b>{total_losses}</b>",
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Поставлено: <b>{total_bet_sum:.0f}</b>",
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Выиграно: <b>{total_win_sum:.0f}</b>",
        f"<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Чистый итог: <b>{net_str}</b>",
    ]
    await message.answer("\n".join(lines), reply_markup=profile_back_kb())

async def render_help(cb_or_msg, page: int):
    total = len(HELP_PAGES)
    if page < 0: page = 0
    if page >= total: page = total - 1
    
    page_content = HELP_PAGES[page]
    if isinstance(page_content, tuple):
        text = "\n".join(page_content)
    else:
        text = page_content
    
    markup = help_kb(page, total)
    
    if isinstance(cb_or_msg, CallbackQuery):
        try:
            # Отправляем новым сообщением (не edit)
            await cb_or_msg.message.answer(text, reply_markup=markup, parse_mode="HTML")
            # Удаляем старое
            try:
                await cb_or_msg.message.delete()
            except Exception:
                pass
        except Exception as e:
            print(f"[Помощь] Ошибка: {e}")
            # Fallback — без премиума
            import re
            clean = re.sub(r"([^<]+)", r"\1", text)
            try:
                await cb_or_msg.message.answer(clean, reply_markup=markup, parse_mode="HTML")
                try:
                    await cb_or_msg.message.delete()
                except Exception:
                    pass
            except Exception as e2:
                print(f"[Помощь] Fallback ошибка: {e2}")
        try:
            await cb_or_msg.answer()
        except Exception:
            pass
    else:
        try:
            await cb_or_msg.answer(text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            print(f"[Помощь] Ошибка: {e}")


@dp.callback_query(F.data == "help_noop")
async def help_noop(cb: CallbackQuery):
    await cb.answer()




@dp.message(Command("broadcast"))
@admin_only
async def cmd_broadcast(message: Message):
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Формат: /broadcast ТЕКСТ")
        return
    await message.answer("📢 Рассылка запущена...")
    ids = await get_all_user_ids()
    sent = 0
    failed = 0
    for uid in ids:
        if uid == message.from_user.id:
            continue
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"✅ Отправлено: {sent}\n<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Ошибок: {failed}")



@dp.message(Command("give"))
@admin_only
async def cmd_give(message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Формат: /give ID СУММА")
        return
    try:
        uid = int(args[1])
        amount = float(args[2])
    except ValueError:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> ID и сумма должны быть числами")
        return
    user = await get_user(uid)
    if not user:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Пользователь не найден")
        return
    await update_balance(uid, amount)
    new_bal = await get_balance(uid)
    await message.answer(f"✅ Выдано {amount:.0f} монет игроку {uid}\n<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {new_bal:.0f}")
    try:
        await bot.send_message(uid, f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Тебе начислено +{amount:.0f} монет админом!")
    except Exception:
        pass



@dp.message(Command("ban"))
@admin_only
async def cmd_ban(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /ban ID")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> ID должен быть числом")
        return
    await set_banned(uid, True)
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = 0, last_bet = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    await message.answer(f"⚠️ 🫥 Игрок {uid} забанен, баланс обнулён")


@dp.message(Command("unban"))
@admin_only
async def cmd_unban(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /unban ID")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> ID должен быть числом")
        return
    await set_banned(uid, False)
    await message.answer(f"✅ Игрок {uid} разбанен")



@dp.message(Command("botstats"))
@admin_only
async def cmd_botstats(message: Message):
    s = await bot_stats()
    net = s["won"] - s["wagered"]
    net_str = f"+{net:.0f}" if net >= 0 else f"{net:.0f}"
    await message.answer(
        f"<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> <b>Статистика бота</b>\n\n"
        f"👥 Игроков: <b>{s['users']}</b>\n"
        f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Всего ставок: <b>{s['bets']}</b>\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Поставлено: <b>{s['wagered']:.0f}</b>\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Выиграно: <b>{s['won']:.0f}</b>\n"
        f"<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Чистый итог казино: <b>{net_str}</b>\n\n"
        f"<tg-emoji emoji-id='5208962449989988262'>🎟</tg-emoji> Промокодов: <b>{s['promos']}</b>\n"
        f"<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji> Джекпот: <b>{s['jackpot']:.0f}</b>"
    )



@dp.message(Command("admin"))
@admin_only
async def cmd_admin_help(message: Message):
    await message.answer(
        "<tg-emoji emoji-id='5192881946404874629'>🔧</tg-emoji> <b>Админ-команды</b>\n\n"
        "📢 /broadcast ТЕКСТ — рассылка всем\n"
        "💰 /give ID СУММА — выдать монеты\n"
        "🚫 /ban ID — забанить\n"
        "✅ /unban ID — разбанить\n"
        "📊 /botstats — статистика бота\n\n"
        "<tg-emoji emoji-id='5208962449989988262'>🎟</tg-emoji> /addpromo КОД СУММА КОЛ-ВО\n"
        "<tg-emoji emoji-id='5445267414562389170'>🗑</tg-emoji> /delpromo КОД\n"
        "<tg-emoji emoji-id='5408946052961170713'>📋</tg-emoji> /promos"
    )

@dp.callback_query(F.data == "vip")
async def vip_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    level = await get_vip(cb.from_user.id)
    bal = await get_balance(cb.from_user.id)
    name = VIP_NAMES.get(level, "\u0411\u0435\u0437 VIP")
    price1 = VIP_PRICES[1]
    price2 = VIP_PRICES[2]
    text = (
        "<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> <b>VIP-\u0441\u0442\u0430\u0442\u0443\u0441</b>\n\n"
        "📊 \u0422\u0432\u043e\u0439 \u0441\u0442\u0430\u0442\u0443\u0441: <b>" + name + "</b>\n"
        "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> \u0411\u0430\u043b\u0430\u043d\u0441: <b>" + f"{bal:.0f}" + "</b>\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "<tg-emoji emoji-id='6084472459329800521'>🥈</tg-emoji> <b>Silver \u2014 " + f"{price1:,}".replace(",", " ") + " \u043c\u043e\u043d\u0435\u0442</b>\n"
        "\u2022 +5% \u043a \u0432\u044b\u0438\u0433\u0440\u044b\u0448\u0443\n"
        "\u2022 \u0411\u043e\u043d\u0443\u0441 750 \u043c\u043e\u043d\u0435\u0442\n\n"
        "<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> <b>Gold \u2014 " + f"{price2:,}".replace(",", " ") + " \u043c\u043e\u043d\u0435\u0442</b>\n"
        "\u2022 +10% \u043a \u0432\u044b\u0438\u0433\u0440\u044b\u0448\u0443\n"
        "\u2022 \u0411\u043e\u043d\u0443\u0441 1000 \u043c\u043e\u043d\u0435\u0442\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"
    )
    await cb.message.edit_text(text, reply_markup=vip_menu_kb(level))
    await cb.answer()


@dp.callback_query(F.data == "vip_my")
async def vip_my(cb: CallbackQuery):
    level = await get_vip(cb.from_user.id)
    name = VIP_NAMES.get(level, "\u0411\u0435\u0437 VIP")
    bonus = VIP_BONUS.get(level, 500)
    mult = VIP_MULTIPLIER.get(level, 1.0)
    pct = int((mult - 1) * 100)
    text = (
        "📊 <b>\u0422\u0432\u043e\u0439 VIP</b>\n\n"
        "\u0421\u0442\u0430\u0442\u0443\u0441: <b>" + name + "</b>\n"
        "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> \u0411\u043e\u043d\u0443\u0441: <b>+" + str(pct) + "%</b>\n"
        "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> \u0411\u043e\u043d\u0443\u0441: <b>" + str(bonus) + "</b> \u043c\u043e\u043d\u0435\u0442"
    )
    await cb.message.edit_text(text, reply_markup=vip_menu_kb(level))
    await cb.answer()


@dp.callback_query(F.data.startswith("vip_buy_"))
async def vip_buy(cb: CallbackQuery):
    try:
        level = int(cb.data.split("_")[-1])
    except ValueError:
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
        return
    if level not in VIP_PRICES:
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
        return
    price = VIP_PRICES[level]
    name = VIP_NAMES[level]
    current = await get_vip(cb.from_user.id)
    if current >= level:
        await cb.answer("\u0423\u0436\u0435 \u0435\u0441\u0442\u044c", show_alert=True)
        return
    emoji = SILVER if level == 1 else CROWN
    text = (
        "❓ <b>\u041f\u043e\u043a\u0443\u043f\u043a\u0430 " + name + "</b> " + emoji + "\n\n"
        "\u0426\u0435\u043d\u0430: <b>" + f"{price:,}".replace(",", " ") + "</b> \u043c\u043e\u043d\u0435\u0442\n"
        "\u041d\u0430\u0432\u0441\u0435\u0433\u0434\u0430.\n\n\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c?"
    )
    await cb.message.edit_text(text, reply_markup=vip_confirm_kb(level))
    await cb.answer()


@dp.callback_query(F.data.startswith("vip_confirm_"))
async def vip_confirm(cb: CallbackQuery):
    try:
        level = int(cb.data.split("_")[-1])
    except ValueError:
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
        return
    if level not in VIP_PRICES:
        await cb.answer("\u041e\u0448\u0438\u0431\u043a\u0430", show_alert=True)
        return
    price = VIP_PRICES[level]
    name = VIP_NAMES[level]
    bal = await get_balance(cb.from_user.id)
    if bal < price:
        await cb.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> \u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e", show_alert=True)
        return
    await update_balance(cb.from_user.id, -price)
    await set_vip(cb.from_user.id, level)
    new_bal = await get_balance(cb.from_user.id)
    emoji = SILVER if level == 1 else CROWN
    text = (
        "🎉 <b>\u041f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f\u0435\u043c!</b>\n\n"
        "\u0422\u044b \u043f\u043e\u043b\u0443\u0447\u0438\u043b " + emoji + " <b>" + name + "</b>!\n\n"
        "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> \u0421\u043f\u0438\u0441\u0430\u043d\u043e: <b>" + f"{price:,}".replace(",", " ") + "</b>\n"
        "<tg-emoji emoji-id='5334708741545680612'>💼</tg-emoji> \u041e\u0441\u0442\u0430\u0442\u043e\u043a: <b>" + f"{new_bal:.0f}" + "</b>"
    )
    await cb.message.edit_text(text, reply_markup=vip_menu_kb(level))
    await cb.answer("VIP \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d!")


@dp.message(Command("testanim"))
@admin_only
async def cmd_testanim(message: Message):

    DUEL = "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji>"
    TOP = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"

    amount = 500
    chat_id = message.chat.id
    test_code = f"TEST_{message.from_user.id}"

    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM duels WHERE code = ?", (test_code,))
        await db.execute(
            "INSERT INTO duels (code, creator_id, opponent_id, amount, status, created_at) VALUES (?, ?, ?, ?, 'active', ?)",
            (test_code, message.from_user.id, 999999, amount, int(time.time()))
        )
        await db.commit()

    await message.answer(
        DUEL + " <b>Тест дуэли</b>\n\n"
        + DOLLAR + f" Ставка: <b>{amount}</b> монет"
    )
    await asyncio.sleep(1)

    p1_roll = random.randint(1, 6)
    p2_roll = random.randint(1, 6)
    while p1_roll == p2_roll:
        p1_roll = random.randint(1, 6)
        p2_roll = random.randint(1, 6)

    frames = [(random.randint(1, 6), random.randint(1, 6)) for _ in range(9)]
    await animate_cubes(chat_id, p1_roll, p2_roll, frames)
    await asyncio.sleep(0.8)

    if p1_roll > p2_roll:
        cube_winner = message.from_user.id
        await set_duel_rolls(test_code, p1_roll, p2_roll, cube_winner)
        text = (
            TOP + " <b>Кубики брошены!</b>\n\n"
            + f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>{p1_roll} : {p2_roll}</b>\n\n"
            + TOP + " Ты победил в кубике!\n\n"
            + "Выбери сторону:"
        )
        await message.answer(text, reply_markup=duel_side_kb(test_code))
    else:
        text = (
            TOP + " <b>Кубики брошены!</b>\n\n"
            + f"<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>{p1_roll} : {p2_roll}</b>\n\n"
            + "😭 Противник победил в кубике.\n"
            + "Он выбирает сторону..."
        )
        await message.answer(text)
        await asyncio.sleep(2)
        auto_side = random.choice(["eagle", "star"])
        await continue_testanim(message, test_code, auto_side, amount)


async def continue_testanim(message: Message, test_code: str, side: str, amount: int):
    COIN = "🪙"
    CHECK = "✅"
    EAGLE_EMOJI = "🦅"
    STAR_EMOJI = "<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji>"
    TOP = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>"
    SAD = "😭"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"

    if side == "eagle":
        my_label = EAGLE_EMOJI + " Орёл"
        opp_label = STAR_EMOJI + " Решка"
    else:
        my_label = STAR_EMOJI + " Решка"
        opp_label = EAGLE_EMOJI + " Орёл"

    await message.answer(
        CHECK + f" Ты выбрал: <b>{my_label}</b>\n"
        + "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Противник получит: <b>" + opp_label + "</b>"
    )
    await asyncio.sleep(1.2)

    coin_result = random.choice(["eagle", "star"])
    await animate_coin(message.chat.id, coin_result)
    await asyncio.sleep(0.8)

    if coin_result == side:
        text = TOP + " <b>Ты победил!</b>\n\n" + DOLLAR + f" +<b>{amount}</b> монет"
    else:
        text = SAD + " <b>Ты проиграл!</b>\n\n" + DOLLAR + f" -<b>{amount}</b> монет"

    await message.answer(text)


@dp.errors()
async def errors_handler(event: types.ErrorEvent):
    exc = event.exception
    # Игнорируем "message is not modified" — это не баг
    if hasattr(exc, "message") and "message is not modified" in str(exc.message):
        return True
    # Остальные ошибки логируем
    import logging
    logging.exception(f"Ошибка в хендлере: {exc}")
    return True



@dp.message(Command("extractemoji"))
async def cmd_extractemoji(message: Message):
    await message.answer(
        "👀 Отправь мне **сообщение с премиум-эмодзи** (скопируй из любого чата) — я покажу их ID."
    )



@dp.message(F.forward_date)
async def extract_emoji_from_msg(message: Message):
    from aiogram.types import MessageEntity
    custom = [e for e in message.entities if e.type == "custom_emoji"]
    if not custom:
        return
    lines = ["🔍 <b>Найдены премиум-эмодзи:</b>\n"]
    for e in custom:
        # Извлекаем текст по offset/length
        text = message.text or message.caption or ""
        emoji = text[e.offset:e.offset + e.length]
        lines.append(f"<code>{emoji}</code> → ID: <code>{e.custom_emoji_id}</code>")
    await message.answer("\n".join(lines))



@dp.callback_query(F.data.startswith("duelside_"))
async def duel_choose_side(cb: CallbackQuery):
    # Формат: duelside_{side}_{code}
    # code может содержать _
    payload = cb.data.replace("duelside_", "", 1)
    # Первая часть до _ это side
    if "_" not in payload:
        await cb.answer("Ошибка", show_alert=True)
        return
    side, code = payload.split("_", 1)
    
    if side not in ("eagle", "star"):
        await cb.answer("Ошибка", show_alert=True)
        return
    
    # Тестовый режим
    if code.startswith("TEST_"):
        try:
            await cb.message.edit_text("✅ Выбрано!")
        except Exception:
            pass
        await cb.answer("Принято")
        await continue_testanim(cb.message, code, side, 500)
        return
    
    duel = await get_duel(code)
    if not duel or duel["status"] != "active":
        await cb.answer("Дуэль неактивна", show_alert=True)
        return
    if cb.from_user.id != duel["cube_winner"]:
        await cb.answer("Только победитель кубика выбирает", show_alert=True)
        return
    if duel["chosen_side"]:
        await cb.answer("Сторона уже выбрана", show_alert=True)
        return
    
    await set_duel_side(code, side)
    
    COIN = "🪙"
    EAGLE_EMOJI = "🦅"
    STAR_EMOJI = "<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji>"
    CHECK = "✅"
    TOP = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>"
    SAD = "😭"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"
    
    if side == "eagle":
        my_label = EAGLE_EMOJI + " Орёл"
        opp_label = STAR_EMOJI + " Решка"
    else:
        my_label = STAR_EMOJI + " Решка"
        opp_label = EAGLE_EMOJI + " Орёл"
    
    if duel["creator_id"] == cb.from_user.id:
        opponent_id = duel["opponent_id"]
    else:
        opponent_id = duel["creator_id"]
    
    try:
        await cb.message.edit_text(
            CHECK + f" Ты выбрал: <b>{my_label}</b>\n"
            + "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Противник получит: <b>" + opp_label + "</b>\n\n"
            + COIN + " Бросаем монетку..."
        )
    except Exception:
        pass
    await cb.answer()
    
    try:
        await bot.send_message(
            opponent_id,
            "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> <b>Твоя сторона:</b> " + opp_label + "\n\n"
            + COIN + " Бросаем монетку..."
        )
    except Exception:
        pass
    
    await asyncio.sleep(1.5)
    
    coin_result = random.choice(["eagle", "star"])
    await animate_coin(cb.message.chat.id, coin_result)
    try:
        await animate_coin(opponent_id, coin_result)
    except Exception:
        pass
    await asyncio.sleep(0.8)
    
    if coin_result == side:
        duel_winner = cb.from_user.id
    else:
        duel_winner = opponent_id
    duel_loser = opponent_id if duel_winner == cb.from_user.id else cb.from_user.id
    
    amount = duel["amount"]
    await update_balance(duel_winner, amount * 2)
    await finish_duel(code, duel_winner)
    await add_history(duel_winner, "duel_win", amount, 0, amount * 2)
    await add_history(duel_loser, "duel_lose", amount, 0, 0)
    
    is_winner_me = duel_winner == cb.from_user.id
    
    if is_winner_me:
        my_text = TOP + " <b>Ты победил!</b>\n\n" + DOLLAR + f" +<b>{amount:.0f}</b> монет"
        opp_text = SAD + " <b>Ты проиграл.</b>\n\n" + DOLLAR + f" -<b>{amount:.0f}</b> монет"
    else:
        my_text = SAD + " <b>Ты проиграл.</b>\n\n" + DOLLAR + f" -<b>{amount:.0f}</b> монет"
        opp_text = TOP + " <b>Ты победил!</b>\n\n" + DOLLAR + f" +<b>{amount:.0f}</b> монет"
    
    try:
        await bot.send_message(duel_winner, my_text if is_winner_me else opp_text)
    except Exception:
        pass
    try:
        await bot.send_message(duel_loser, opp_text if is_winner_me else my_text)
    except Exception:
        pass


async def animate_cubes(chat_id, final1, final2, frames=None):
    """Анимирует показ двух кубиков текстом. Одинаковые кадры при передаче frames."""
    if frames is None:
        frames = [(random.randint(1, 6), random.randint(1, 6)) for _ in range(9)]

    DICE = "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji>"

    try:
        msg = await bot.send_message(
            chat_id,
            DICE + " <b>Бросаем кубики...</b>\n\n"
            "<code>┃ ? ┃ ┃ ? ┃</code>"
        )
    except Exception:
        return None

    # Фаза 1: быстро (5 кадров по 0.3с)
    for i in range(5):
        await asyncio.sleep(0.3)
        a, b = frames[i]
        try:
            await msg.edit_text(
                DICE + " <b>Бросаем кубики...</b>\n\n"
                f"<code>┃ {a} ┃ ┃ {b} ┃</code>"
            )
        except Exception:
            pass

    # Фаза 2: медленнее (3 кадра по 0.5с)
    for i in range(5, 8):
        await asyncio.sleep(0.5)
        a, b = frames[i]
        try:
            await msg.edit_text(
                DICE + " <b>Бросаем кубики...</b>\n\n"
                f"<code>┃ {a} ┃ ┃ {b} ┃</code>"
            )
        except Exception:
            pass

    # Финальная пауза
    await asyncio.sleep(0.8)

    # Финал
    try:
        await msg.edit_text(
            DICE + " <b>Результат:</b>\n\n"
            f"<code>┃ {final1} ┃ ┃ {final2} ┃</code>"
        )
    except Exception:
        pass
    return msg


async def animate_coin(chat_id, final_side):
    # Финальные премиум-эмодзи
    EAGLE = "🦅"
    STAR = "<tg-emoji emoji-id='6168024652867178337'>🌟</tg-emoji>"

    # Анимация: монетка падает сверху вниз
    frames = [
        # Монетка высоко
        "🪙 <b>Бросаем монетку...</b>\n\n\n\n\n         🪙",
        # Чуть ниже
        "🪙 <b>Бросаем монетку...</b>\n\n\n         🪙\n\n",
        # Ниже
        "🪙 <b>Бросаем монетку...</b>\n\n      🪙\n\n\n",
        # Ещё ниже
        "🪙 <b>Бросаем монетку...</b>\n\n   🪙\n\n\n\n",
        # Совсем рядом
        "🪙 <b>Бросаем монетку...</b>\n\n🪙\n\n\n\n\n",
        # Кадр вращения
        "🪙 <b>Бросаем монетку...</b>\n\n         🪙\n         ⬇️",
    ]

    try:
        msg = await bot.send_message(
            chat_id,
            frames[0],
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"COIN ERR: {e}")
        return None

    for f in frames[1:]:
        await asyncio.sleep(0.35)
        try:
            await msg.edit_text(f, parse_mode="HTML")
        except Exception:
            pass

    await asyncio.sleep(0.6)

    # Финальный кадр
    if final_side == "eagle":
        result = EAGLE + " <b>ОРЁЛ!</b>"
    else:
        result = STAR + " <b>РЕШКА!</b>"

    try:
        await msg.edit_text(
            "🪙 <b>Монетка упала:</b>\n\n         " + result,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"COIN EDIT ERR: {e}")
    return msg


@dp.message(Command("addref"))
@admin_only
async def cmd_addref(message: Message):
    """Формат: /addref ID_друга — засчитать друга как реферала ТЕБЕ"""
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "Формат: <code>/addref ID_друга</code>\n"
            "Пример: <code>/addref 123456789</code>\n\n"
            "Засчитает юзера как твоего реферала."
        )
        return
    try:
        friend_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    if friend_id == message.from_user.id:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Нельзя себя")
        return
    
    friend = await get_user(friend_id)
    if not friend:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Юзер {friend_id} не найден в боте")
        return
    
    if friend["referred_by"]:
        await message.answer(
            f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Уже есть реферер: <code>{friend['referred_by']}</code>\n"
            f"Сначала убери: <code>/delref {friend_id}</code>"
        )
        return
    
    # Устанавливаем реферера
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET referred_by = ? WHERE user_id = ?",
            (message.from_user.id, friend_id)
        )
        await db.commit()
    
    # Начисляем бонус
    await update_balance(message.from_user.id, 1300)
    
    await message.answer(
        f"✅ Засчитан реферал!\n\n"
        f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Друг: <code>{friend_id}</code> @{friend['username']}\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> +1300 монет тебе"
    )



@dp.message(Command("delref"))
async def cmd_delref(message: Message):
    """Формат: /delref ID — убрать реферала у юзера"""
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: <code>/delref ID_юзера</code>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET referred_by = NULL WHERE user_id = ?", (uid,))
        await db.commit()
    
    await message.answer(f"✅ У юзера <code>{uid}</code> убран реферер")



@dp.message(Command("whoinvited"))
@admin_only
async def cmd_whoinvited(message: Message):
    """Кто кого пригласил"""
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u1.user_id, u1.username, u1.referred_by, u2.username as referrer_name
            FROM users u1
            LEFT JOIN users u2 ON u2.user_id = u1.referred_by
            WHERE u1.referred_by IS NOT NULL
            ORDER BY u1.user_id
        """) as c:
            rows = await c.fetchall()
    
    if not rows:
        await message.answer("📭 Рефералов нет")
        return
    
    lines = ["🔗 <b>Все рефералы:</b>\n"]
    for r in rows:
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        ref_name = f"@{r['referrer_name']}" if r['referrer_name'] else f"ID {r['referred_by']}"
        lines.append(f"👤 {name} ← от {ref_name}")
    
    await message.answer("\n".join(lines))

@dp.message(Command("resetref"))
@admin_only
async def cmd_resetref(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /resetref ID")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT referred_by FROM users WHERE user_id = ?", (uid,)) as c:
            row = await c.fetchone()
        referrer_id = row[0] if row else None
        await db.execute("UPDATE users SET referred_by = NULL WHERE user_id = ?", (uid,))
        if referrer_id:
            await db.execute("UPDATE users SET balance = MAX(0, balance - 1300) WHERE user_id = ?", (referrer_id,))
        await db.commit()
    await message.answer(f"✅ У юзера {uid} сброшен реферер, у пригласившего вычтено 1300")



@dp.message(Command("myrefs"))
@admin_only
async def cmd_myrefs(message: Message):
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username FROM users WHERE referred_by = ?", (message.from_user.id,)) as c:
            rows = await c.fetchall()
    if not rows:
        await message.answer("<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> У тебя нет рефералов")
        return
    lines = [f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Твои рефералы ({len(rows)}):"]
    for r in rows:
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        lines.append(f"• {name}")
    await message.answer("\n".join(lines))



@dp.message(Command("testref"))
@admin_only
async def cmd_testref(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /testref ID")
        return
    try:
        fake_user_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    user = await get_user(fake_user_id)
    if not user:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Юзер {fake_user_id} не найден")
        return
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET referred_by = NULL WHERE user_id = ?", (fake_user_id,))
        await db.commit()
    ok = await set_referrer(fake_user_id, message.from_user.id)
    if ok:
        await update_balance(message.from_user.id, REFERRAL_BONUS)
        refs = await get_referrals_count(message.from_user.id)
        await message.answer(
            f"✅ Симуляция!\n\n"
            f"<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji> Друг: {fake_user_id} @{user['username']}\n"
            f"💰 +{REFERRAL_BONUS}\n"
            f"👥 Всего: {refs}"
        )
    else:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Не удалось")

@dp.message(Command("orphans"))
@admin_only
async def cmd_orphans(message: Message):
    FRIEND = "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji>"
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, username, created_at
            FROM users
            WHERE referred_by IS NULL AND agreed = 1
            ORDER BY created_at DESC
            LIMIT 30
        """) as c:
            rows = await c.fetchall()
    
    if not rows:
        await message.answer(FRIEND + " Нет юзеров без реферера")
        return
    
    import datetime
    lines = [FRIEND + f" <b>Без реферера ({len(rows)}):</b>\n"]
    for r in rows:
        name = f"@{r['username']}" if r['username'] else f"ID {r['user_id']}"
        try:
            dt = datetime.datetime.fromtimestamp(r['created_at']).strftime("%d.%m %H:%M")
        except Exception:
            dt = "?"
        lines.append(f"• {name} · {dt}")
    
    await message.answer("\n".join(lines))


@dp.message(Command("setbal"))
@admin_only
async def cmd_setbal(message: Message):
    """Формат: /setbal ID СУММА — установить баланс"""
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Формат: /setbal ID СУММА")
        return
    try:
        uid = int(args[1])
        amount = float(args[2])
    except ValueError:
        await message.answer("ID и сумма должны быть числами")
        return
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, uid))
        await db.commit()
    
    CHECK = "✅"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"
    await message.answer(
        f"{CHECK} Баланс юзера <code>{uid}</code> установлен: {DOLLAR} <b>{amount:.0f}</b>"
    )



@dp.message(Command("setjackpot"))
@admin_only
async def cmd_setjackpot(message: Message):
    """Формат: /setjackpot СУММА"""
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /setjackpot СУММА")
        return
    try:
        amount = float(args[1])
    except ValueError:
        await message.answer("Сумма должна быть числом")
        return
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE jackpot SET amount = ? WHERE id = 1", (amount,))
        await db.commit()
    
    CHECK = "✅"
    DIAM = "<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji>"
    await message.answer(
        f"{CHECK} Джекпот установлен: {DIAM} <b>{amount:.0f}</b>"
    )



@dp.message(Command("givejackpot"))
@admin_only
async def cmd_givejackpot(message: Message):
    """Формат: /givejackpot ID — выдать джекпот юзеру"""
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /givejackpot ID")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT amount FROM jackpot WHERE id = 1") as c:
            row = await c.fetchone()
            jackpot = float(row[0]) if row else 0.0
        await db.execute("UPDATE jackpot SET amount = 1000 WHERE id = 1")
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (jackpot, uid))
        await db.commit()
    
    CHECK = "✅"
    DIAM = "<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji>"
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"
    await message.answer(
        f"{CHECK} Джекпот <b>{jackpot:.0f}</b> {DIAM} выдан юзеру <code>{uid}</code>\n"
        f"{DOLLAR} Джекпот сброшен до 1000"
    )



@dp.message(Command("resetbal"))
@admin_only
async def cmd_resetbal(message: Message):
    """Формат: /resetbal ID — обнулить баланс"""
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /resetbal ID")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = 0, last_bet = 0 WHERE user_id = ?", (uid,))
        await db.commit()
    
    CHECK = "✅"
    await message.answer(f"{CHECK} Баланс юзера <code>{uid}</code> обнулён")



@dp.message(Command("paycheck"))
@admin_only
async def cmd_paycheck(message: Message):
    """Показать текущий баланс и джекпот"""
    import aiosqlite
    from config import DB_NAME
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as c:
            row = await c.fetchone()
            bal = float(row[0]) if row else 0.0
        async with db.execute("SELECT amount FROM jackpot WHERE id = 1") as c:
            row = await c.fetchone()
            jp = float(row[0]) if row else 0.0
    
    DOLLAR = "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>"
    DIAM = "<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji>"
    await message.answer(
        f"{DOLLAR} Баланс: <b>{bal:.0f}</b>\n"
        f"{DIAM} Джекпот: <b>{jp:.0f}</b>"
    )








@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    uid = message.from_user.id
    bal = await get_balance(uid)
    vip = await get_vip(uid)
    name = VIP_NAMES.get(vip, "Обычный")
    await message.answer(
        f"<tg-emoji emoji-id='5294079931473477913'>📃</tg-emoji> <b>Профиль</b>\n"
        f"<tg-emoji emoji-id='5841276284155467413'>🔤</tg-emoji> ID: <code>{uid}</code>\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {bal} монет\n"
        f"<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> VIP: {name}"
    )


@dp.message(Command("bonus"))
async def cmd_bonus(message: Message):
    import time
    uid = message.from_user.id
    last = await get_last_bonus(uid)
    now = time.time()
    vip = await get_vip(uid)
    cd = VIP_COOLDOWN.get(vip, BONUS_COOLDOWN)
    amt = VIP_BONUS.get(vip, BONUS_AMOUNT)
    if now - last < cd:
        left = int(cd - (now - last))
        await message.answer(f"<tg-emoji emoji-id='5292259724333433172'>⏰</tg-emoji> Бонус через {fmt_time(left)}")
        return
    await update_balance(uid, amt)
    await set_last_bonus(uid, now)
    await message.answer(f"<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Бонус: +{amt} монет!")


@dp.message(Command("history"))
async def cmd_history(message: Message):
    uid = message.from_user.id
    history = await get_history(uid, limit=10)
    if not history:
        await message.answer("История пуста")
        return
    text = "<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> <b>История:</b>\n"
    for h in history:
        text += f"• {h}\n"
    await message.answer(text)


@dp.message(Command("vip"))
async def cmd_vip(message: Message):
    uid = message.from_user.id
    lvl = await get_vip(uid)
    name = VIP_NAMES.get(lvl, "Обычный")
    bal = await get_balance(uid)
    
    text = (
        "VIP <b>VIP-статус</b>\n\n"
        f"<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Твой статус: <b>{name}</b>\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {bal:.0f}\n\n"
        f"<tg-emoji emoji-id='5370698570326356088'><tg-emoji emoji-id='5370698570326356088'>⭐</tg-emoji>️</tg-emoji> <b>Silver</b> — 120 000 монет\n"
        "• +5% к выигрышу\n"
        "• Бонус 750 монет\n\n"
        f"<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> <b>Gold</b> — 600 000 монет\n"
        "• +10% к выигрышу\n"
        "• Бонус 1000 монет"
    )
    await message.answer(text)

@dp.callback_query(F.data == "vip")
async def cb_vip(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    lvl = await get_vip(uid)
    name = VIP_NAMES.get(lvl, "Обычный")
    mult = VIP_MULTIPLIER.get(lvl, 1.0)
    bon = VIP_BONUS.get(lvl, 0)
    cd = VIP_COOLDOWN.get(lvl, 0)
    text = (
        "<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> <b>Ваш VIP-статус:</b> " + str(name) + "\n"
        + "<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Множитель: x" + str(mult) + "\n"
        + "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Бонус: " + str(bon) + " монет\n"
        + "<tg-emoji emoji-id='5292259724333433172'>⏰</tg-emoji> Кулдаун: " + fmt_time(cd) + "\n\n"
        + "<b>Доступные VIP:</b>\n"
        + "<tg-emoji emoji-id='6084472459329800521'>🥈</tg-emoji> Silver (120к) - 1900 / 1ч 50мин\n"
        + "<tg-emoji emoji-id='5195141017598175832'>🥇</tg-emoji> Gold (600к) - 3500 / 1 час\n"
        + "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Обычным - 700 / 3 часа"
    )
    await callback.message.answer(text)


@dp.message(Command("unlockall"))
@admin_only
async def cmd_unlockall(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unlockall ID")
        return
    try:
        uid = int(args[1])
        if isinstance(ACHIEVEMENTS, dict):
            keys = list(ACHIEVEMENTS.keys())
        elif isinstance(ACHIEVEMENTS, (list, tuple)):
            keys = [a[0] if isinstance(a, (tuple, list)) else a for a in ACHIEVEMENTS]
        else:
            keys = []
        for k in keys:
            await unlock_achievement(uid, k)
        await message.answer(f"✅ Выданы все достижения для {uid}")
    except Exception as e:
        await message.answer(f"<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> {e}")




def fmt_time(seconds: int) -> str:
    """Форматирует секунды в часы/минуты"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0 and m > 0:
        return f"{h}ч {m}мин"
    elif h > 0:
        return f"{h}ч"
    else:
        return f"{m}мин"



# ============ ПОЧИНКА НИЖНЕЙ КНОПКИ "ИГРАТЬ" ============
@dp.message(F.text.contains("Играть"))
async def reply_play_btn(message: Message, state: FSMContext):
    await state.clear()
    bal = await get_balance(message.from_user.id)
    from keyboards import games_kb
    await message.answer(
        f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> <b>Выбери игру:</b>\n\n"
        f"<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> Баланс: {bal:.0f} монет",
        reply_markup=games_kb()
    )

# ============ НАСТРОЙКИ ПРОФИЛЯ (НИК) ============
@dp.callback_query(F.data == "settings")
async def cb_settings(cb: CallbackQuery):
    await cb.answer()
    text = (
        "<b><tg-emoji emoji-id='5467687036473336725'>⚙️</tg-emoji> Настройки</b>\n\n"
        "<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> <b>Установить ник</b> — задаёт твой ник для топа\n"
        "👤 <b>Показывать в топе</b> — ник или @username\n"
        "<tg-emoji emoji-id='5445267414562389170'>🗑</tg-emoji> <b>Удалить ник</b> — убрать ник"
    )
    try:
        await cb.message.edit_text(text, reply_markup=settings_kb())
    except Exception:
        await cb.message.answer(text, reply_markup=settings_kb())

@dp.callback_query(F.data == "setnick_btn")
async def cb_setnick_btn(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> Напиши: <code>/setnick ТВОЙ_НИК</code>\nНапример: <code>/setnick Вася</code>\n\nНик до 20 символов. Без мата и рекламы (твич, ссылки).")

@dp.callback_query(F.data == "settops_btn")
async def cb_settops_btn(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("👤 Напиши:\n<code>/settops nick</code> — показывать ник в топе\n<code>/settops user</code> — показывать @username")

@dp.callback_query(F.data == "clearnick_btn")
async def cb_clearnick_btn(cb: CallbackQuery):
    await cb.answer()
    await clear_nick(cb.from_user.id)
    await cb.message.answer("✅ Ник удалён")


async def cmd_setnick(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Формат: /setnick ТВОЙ_НИК")
    nick = args[1].strip()[:20]
    if len(nick) < 3:
        return await message.answer("Ник слишком короткий (мин. 3 символа)")
        
    bad = ["twitch", "твич", "http", "t.me", "хуй", "пизд", "бля", "еба", "сука", "пидор", "ниггер", "нигга", "член"]
    if any(b in nick.lower() for b in bad):
        return await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Такой ник нельзя использовать.")
            
    import html as _html
    safe_nick = _html.escape(nick)
    await set_nick(message.from_user.id, safe_nick)
    await message.answer(f"✅ Ник установлен: <b>{safe_nick}</b>\n/settops nick — показывать в топе")


async def cmd_settops(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ["nick", "user"]:
        return await message.answer("Формат: /settops nick или /settops user")
    show = 1 if args[1].lower() == "nick" else 0
    await set_show_nick(message.from_user.id, show)
    await message.answer("В топе будет показываться " + ("<b>ник</b>" if show else "<b>@username</b>"))

# ============ ВВОД ПРОМОКОДА ============
@dp.message(Command("promo"))
async def cmd_promo_text(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Введи: <code>/promo КОД</code>")
    code = args[1].strip()
    try:
        success = await use_promo(code.lower(), message.from_user.id)
        if success:
            await message.answer("✅ Промокод активирован!")
        else:
            await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Неверный код или он уже использован.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")




# ============ ТОП ИГРОКОВ (ОБНОВЛЕННЫЙ) ============
async def render_top_data(message_or_cb, page: int, edit: bool = False):
    per_page = 10
    total_limit = 100
    offset = page * per_page
    if offset >= total_limit:
        offset = total_limit - per_page
        page = (total_limit // per_page) - 1
        
    players = await get_top_players(per_page, offset)
    if not players:
        text = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Топ пуст. Стань первым!"
        if edit:
            try: await message_or_cb.edit_text(text, reply_markup=back_kb())
            except: pass
        else:
            await message_or_cb.answer(text, reply_markup=back_kb())
        return

    medals = [
        "🔸",
        "2️⃣",
        "3️⃣",
        "4️⃣",
        "5️⃣",
        "6️⃣",
        "7️⃣",
        "8️⃣",
        "9️⃣",
        "💲"
    ]
    
    total_pages = total_limit // per_page
    lines = [f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Топ игроков</b> ({page+1}/{total_pages})\n"]
    
    for i, p in enumerate(players):
        rank = page * per_page + i + 1
        prefix = medals[rank - 1] if rank <= 10 else f"{rank}."
        
        # ПРОВЕРКА НИКА
        try:
            s_nick = p["show_nick"]
            nick = p["nick"]
        except (KeyError, IndexError):
            s_nick = 0
            nick = None
            
        if s_nick and nick:
            name = f"<b>{nick}</b>"
        else:
            name = filter_username(p["username"], p["user_id"])
            
        # VIP
        try:
            uid = p["user_id"]
        except:
            uid = None
        vip_lvl = await get_vip(uid) if uid else 0
        vip_icon = {1: "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji>", 2: "📔"}.get(vip_lvl, "")
        
        lines.append(f"{prefix} {vip_icon} {name} — <b>{p['balance']:.0f}</b>")
        
    text = "\n".join(lines)
    kb = top_kb(page, total_pages)
    
    if edit:
        try: await message_or_cb.edit_text(text, reply_markup=kb)
        except: pass
    else:
        await message_or_cb.answer(text, reply_markup=kb)


# Кнопка ТОП под сообщением (Inline)

async def cb_top(cb: CallbackQuery):
    await cb.answer()
    await render_top_data(cb.message, 0, edit=True)

# Кнопка ТОП в нижнем меню (Reply)




# ============ ТОП ИГРОКОВ (ЕДИНЫЙ) ============


async def cb_top_new(cb: CallbackQuery):
    await cb.answer()
    await render_top_universal(cb.message, 0, edit=True)

# Кнопка ТОП в нижнем меню (Текст)

async def reply_top_new(message: Message):
    await render_top_universal(message, 0, edit=False)



@dp.message(Command("setnick"))
async def cmd_setnick(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> Формат: /setnick ТВОЙ_НИК")
    nick = args[1].strip()[:20]
    if len(nick) < 3:
        return await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Ник слишком короткий (мин. 3 символа)")
        
    bad = ["twitch", "твич", "http", "t.me", "хуй", "пизд", "бля", "еба", "сука", "пидор", "ниггер", "нигга", "член"]
    if any(b in nick.lower() for b in bad):
        return await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Такой ник нельзя использовать.")
            
    import html as _html
    safe_nick = _html.escape(nick)
    await set_nick(message.from_user.id, safe_nick)
    await message.answer(f"✅ Ник установлен: <b>{safe_nick}</b>\n/settops nick — показывать в топе")

@dp.message(Command("settops"))
async def cmd_settops(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        return await message.answer("<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> Формат: /settops nick или /settops user")
        
    mode = args[1].lower()
    
    if mode == "user":
        await set_show_nick(message.from_user.id, 0)
        await message.answer("<tg-emoji emoji-id='5841276284155467413'>🔤</tg-emoji> В топе будет показываться твой <b>@username</b>")
    elif mode == "nick":
        if len(args) >= 3:
            nick = args[2].strip()[:20]
            bad = ["twitch", "твич", "http", "t.me", "хуй", "пизд", "бля", "еба", "сука", "пидор", "ниггер", "нигга", "член"]
            if len(nick) < 3:
                return await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Ник слишком короткий.")
            if any(b in nick.lower() for b in bad):
                return await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Такой ник нельзя использовать.")
            
            import html as _html
            safe_nick = _html.escape(nick)
            await set_nick(message.from_user.id, safe_nick)
            await set_show_nick(message.from_user.id, 1)
            await message.answer(f"✅ Ник изменен на <b>{safe_nick}</b> и будет показываться в топе!")
        else:
            await set_show_nick(message.from_user.id, 1)
            await message.answer("<tg-emoji emoji-id='5841276284155467413'>🔤</tg-emoji> В топе будет показываться твой <b>ник</b>")
    else:
        await message.answer("<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji> Неизвестный параметр. Используй nick или user.")



# ============ ТОП ИГРОКОВ ============
async def render_top_universal(target, page: int, edit: bool = False):
    per_page = 10
    total_limit = 100
    offset = page * per_page
    if offset >= total_limit:
        offset = total_limit - per_page
        page = (total_limit // per_page) - 1

    players = await get_top_players(per_page, offset)
    if not players:
        text = "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Топ пуст. Стань первым!"
        if edit:
            try: await target.edit_text(text, reply_markup=back_kb())
            except: pass
        else:
            await target.answer(text, reply_markup=back_kb())
        return

    medals = [
        "🔸",
        "2️⃣",
        "3️⃣",
        "4️⃣",
        "5️⃣",
        "6️⃣",
        "7️⃣",
        "8️⃣",
        "9️⃣",
        "💲"
    ]

    total_pages = total_limit // per_page
    lines = [f"<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Топ игроков</b> ({page+1}/{total_pages})\n"]

    for i, p in enumerate(players):
        rank = page * per_page + i + 1
        prefix = medals[rank - 1] if rank <= 10 else f"{rank}."

        try:
            s_nick = p["show_nick"]
            nick = p["nick"]
        except (KeyError, IndexError):
            s_nick = 0
            nick = None

        if s_nick and nick:
            name = f"<b>{nick}</b>"
        else:
            name = filter_username(p["username"], p["user_id"])

        try: uid = p["user_id"]
        except: uid = None
        vip_lvl = await get_vip(uid) if uid else 0
        vip_icon = {1: "<tg-emoji emoji-id='5370698570326356088'><tg-emoji emoji-id='5370698570326356088'>⭐</tg-emoji>️</tg-emoji>", 2: "<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji>"}.get(vip_lvl, "")

        lines.append(f"{prefix} {vip_icon} {name} — <b>{p['balance']:.0f}</b>")

    text = "\n".join(lines)
    kb = top_kb(page, total_pages)

    if edit:
        try: await target.edit_text(text, reply_markup=kb)
        except: pass
    else:
        await target.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "top")
async def cb_top_new(cb: CallbackQuery):
    await cb.answer()
    await render_top_universal(cb.message, 0, edit=True)

@dp.callback_query(F.data.startswith("top_"))
async def cb_top_page(cb: CallbackQuery):
    if cb.data == "top_noop": return await cb.answer()
    try:
        page = int(cb.data.split("_")[1])
    except:
        page = 0
    await cb.answer()
    await render_top_universal(cb.message, page, edit=True)

@dp.message(F.text.contains("Топ"))
async def reply_top_new(message: Message):
    await render_top_universal(message, 0, edit=False)


# ============ ИСТОРИЯ ИГР ============
async def render_hist(message: Message, uid: int, page: int, edit: bool):
    per_page = 10
    total = await get_history_count(uid)
    total_pages = min(5, max(1, (total + per_page - 1) // per_page))
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0

    items = await get_history(uid, limit=per_page, offset=page * per_page)

    if not items:
        text = "История пуста. Сыграй первую игру!"
        kb = back_kb()
    else:
        lines = [f"<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> <b>История</b> ({page+1}/{total_pages})\n"]
        
        # Словарь для перевода названий игр в эмодзи
        game_emojis = {
            "predict": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кубик",
            "basket_predict": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Прогноз баскет",
            "football_predict": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Прогноз футбол",
            "slots": "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Слоты",
            "dice": "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кости",
            "darts": "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Дартс",
            "basketball": "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскет",
            "football": "<tg-emoji emoji-id='5776422093302273080'><tg-emoji emoji-id='5776422093302273080'>⚽</tg-emoji>️</tg-emoji> Футбол",
            "bowling": "<tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> Боулинг",
            "roulette": "<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> Рулетка",
            "duel": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль",
            "duel_win": "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> Дуэль",
        }

        for it in items:
            diff = it["win"] - it["bet"]
            # Берем обычные галочку/крестик
            mark = "✅" if it["win"] > 0 else "<tg-emoji emoji-id='6084880262179588505'>❌</tg-emoji>"
            
            # Переводим название игры
            game_name = it["game"]
            # Если игра есть в словаре, берем эмодзи, иначе пишем как есть
            formatted_game = game_emojis.get(game_name, f"<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> {game_name.capitalize()}")
            
            lines.append(f"{mark} {formatted_game} | {it['bet']:.0f} | {diff:+.0f}")
            
        text = "\n".join(lines)
        kb = history_kb(page, total_pages)

    if edit:
        try: await message.edit_text(text, reply_markup=kb)
        except: pass
    else:
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "history")
async def cb_history(cb: CallbackQuery):
    await cb.answer()
    await render_hist(cb.message, cb.from_user.id, 0, edit=True)

@dp.callback_query(F.data.startswith("hist_"))
async def cb_history_page(cb: CallbackQuery):
    if cb.data == "hist_noop": return await cb.answer()
    try:
        page = int(cb.data.split("_")[1])
    except:
        page = 0
    await cb.answer()
    await render_hist(cb.message, cb.from_user.id, page, edit=True)




async def reply_history_btn(message: Message):
    # Вызываем функцию истории, которая уже есть в коде
    await render_hist(message, message.from_user.id, 0, edit=False)




async def reply_history_fix(message: Message):
    # Вызываем функцию истории, которая уже есть в коде
    await render_hist(message, message.from_user.id, 0, edit=False)



@dp.message(Command("history"))



@dp.message(F.text.contains("История"))
@dp.message(Command("history"))
async def reply_history_fix(message: Message):
    # Вызываем нашу новую функцию render_hist
    await render_hist(message, message.from_user.id, 0, edit=False)







# ============ ПОМОЩЬ С ПАГИНАЦИЕЙ ============





# ============ ЕДИНАЯ ПОМОЩЬ С ПРЕМИУМ-ЭМОДЗИ ============
def _get_help_text(page):
    if page == 0:
        return (
            "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> <b>ПОМОЩЬ (1/3)</b>\n\n"
            "<b>Игры:</b>\n"
            "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji> Слоты · <tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кости · <tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji> Дартс\n"
            "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскет · <tg-emoji emoji-id='5776422093302273080'>⚽️</tg-emoji> Футбол · <tg-emoji emoji-id='5370853837689070338'>🎳</tg-emoji> Боулинг\n"
            "<tg-emoji emoji-id='6127695979404595402'>📱</tg-emoji> Рулетка\n\n"
            "<b>Прогнозы:</b>\n"
            "<tg-emoji emoji-id='5280816565657300091'>🎲</tg-emoji> Кубик — чёт/нечет/точное число\n"
            "<tg-emoji emoji-id='5920095758740098635'>🏀</tg-emoji> Баскет — забьёт/застрянет/мимо\n"
            "<tg-emoji emoji-id='5776422093302273080'>⚽️</tg-emoji> Футбол — гол/штанга/мимо\n\n"
            "<tg-emoji emoji-id='5285133879668137515'>💡</tg-emoji> Выбери игру -> ставку -> смотри результат."
        )
    elif page == 1:
        return (
            "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> <b>ПОМОЩЬ (2/3)</b>\n\n"
            "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> <b>Подарки</b>\n"
            "Передай монеты другому игроку по ID\n\n"
            "<tg-emoji emoji-id='5408935401442267103'>⚔️</tg-emoji> <b>Дуэли</b>\n"
            "Бросок монетки 50/50 с другом\n\n"
            "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> <b>Достижения</b>\n"
            "10 значков за активность\n\n"
            "👥 <b>Рефералка</b>\n"
            "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji> +1300 монет за каждого друга\n\n"
            "<tg-emoji emoji-id='6215092654003195416'>👑</tg-emoji> <b>VIP</b>\n"
            "Silver (120к) и Gold (600к)\n"
            "Бонус: Silver 1900 / 1ч50м, Gold 3500 / 1ч\n"
            "Дают бонусы к выигрышу"
        )
    else:
        return (
            "<tg-emoji emoji-id='6269506208856542101'>🔥</tg-emoji> <b>ПОМОЩЬ (3/3)</b>\n\n"
            "<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji> <b>Джекпот</b>\n"
            "• 3% с каждой ставки -> в банк\n"
            "• Сорвать: выигрыш ×10+ (шанс 1/100)\n"
            "• После срыва сброс до 1000 монет\n\n"
            "<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Бонус — 700 монет раз в 3 часа\n"
            "<tg-emoji emoji-id='5208962449989988262'>🎟️</tg-emoji> Промокод — коды от админа\n"
            "<tg-emoji emoji-id='5303213613220121573'>📈</tg-emoji> Статистика — подробно по играм\n"
            "<tg-emoji emoji-id='5188272613272591128'>📝</tg-emoji> История — последние ставки\n"
            "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Топ игроков — топ-100\n\n"
            "<tg-emoji emoji-id='5253997827788385948'>🎼</tg-emoji> <b>Связь с админом:</b> @Nonsi11"
        )

def _get_help_kb(page):
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"hlp_{page-1}"))
    else:
        row.append(InlineKeyboardButton(text="⬅️", callback_data="hlp_noop"))
    
    row.append(InlineKeyboardButton(text=f"{page+1}/3", callback_data="hlp_noop"))
    
    if page < 2:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"hlp_{page+1}"))
    else:
        row.append(InlineKeyboardButton(text="➡️", callback_data="hlp_noop"))
        
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("help"))
@dp.message(F.text.contains("Помощь"))
async def cmd_help_clean(message: Message):
    await message.answer(_get_help_text(0), reply_markup=_get_help_kb(0))

@dp.callback_query(F.data.startswith("hlp_"))
async def cb_help_clean(cb: CallbackQuery):
    if cb.data == "hlp_noop":
        await cb.answer()
        return
    try:
        page = int(cb.data.split("_")[1])
    except:
        page = 0
    await cb.message.edit_text(_get_help_text(page), reply_markup=_get_help_kb(page))
    await cb.answer()




# ============ СИСТЕМА КЛАНОВ ============

def _nick_is_bad(text):
    bad = ["хуй", "пизд", "блят", "ебат", "сука", "пидор", "ниггер", "нигга", "член", "даун", "уеб"]
    return any(w in text.lower() for w in bad)

@dp.message(Command("clan"))
async def cmd_clan(message: Message):
    args = message.text.split(maxsplit=1)
    uid = message.from_user.id

    if len(args) < 2:
        text = (
            "🛡️ <b>КЛАНЫ</b>\n\n"
            "/clan create ИМЯ — Создать клан (70 000 монет)\n"
            "/clan info — Инфо о твоём клане\n"
            "/clan deposit СУММА — Пополнить казну\n"
            "/clan top — Топ кланов\n"
            "/clan leave — Покинуть клан"
        )
        return await message.answer(text)

    sub = args[1].lower()

    # --- CREATE ---
    if sub.startswith("create"):
        parts = args[1].split(maxsplit=1)
        if len(parts) < 2:
            return await message.answer("Формат: /clan create ИМЯ_КЛАНА")
        clan_name = parts[1].strip()[:20]
        
        if _nick_is_bad(clan_name):
            return await message.answer("❌ Такое название клана нельзя использовать.")
            
        user_clan = await get_clan_by_user(uid)
        if user_clan:
            return await message.answer("❌ Ты уже состоишь в клане.")
            
        bal = await get_balance(uid)
        if bal < 70000:
            return await message.answer(f"❌ Недостаточно монет. Нужно 70 000, у тебя {bal:.0f}.")
            
        success = await create_clan(clan_name, uid)
        if success:
            await update_balance(uid, -70000)
            await message.answer(f"✅ Клан <b>{clan_name}</b> успешно создан!\nСписано 70 000 монет.")
        else:
            await message.answer("❌ Клан с таким названием уже существует.")

    # --- INFO ---
    elif sub == "info":
        clan = await get_clan_by_user(uid)
        if not clan:
            return await message.answer("❌ Ты не состоишь в клане.")
        members = await get_clan_members(clan["id"])
        
        text = f"🛡️ <b>Клан: {clan['name']}</b>\n"
        text += f"👑 Владелец: <a href='tg://user?id={clan['owner_id']}'>ID {clan['owner_id']}</a>\n"
        text += f"👥 Участников: {len(members)}/20\n"
        text += f"💵 Казна: {clan['balance']:.0f} монет\n\n"
        text += "<b>Участники:</b>\n"
        
        for m_row in members:
            if m_row["username"]:
                name = "@" + m_row["username"]
            else:
                name = f"<a href='tg://user?id={m_row['user_id']}'>ID {m_row['user_id']}</a>"
            text += f"• {name}\n"
            
        await message.answer(text)

    # --- DEPOSIT (КАЗНА) ---
    elif sub.startswith("deposit"):
        parts = args[1].split(maxsplit=1)
        if len(parts) < 2:
            return await message.answer("Формат: /clan deposit СУММА")
            
        try:
            amt = float(parts[1])
            if amt <= 0: raise ValueError
        except ValueError:
            return await message.answer("❌ Сумма должна быть числом больше нуля.")
            
        success, msg = await deposit_clan(uid, amt)
        if success:
            await message.answer(f"💵 Ты пополнил казну клана на <b>{amt:.0f}</b> монет!")
        else:
            await message.answer(f"❌ {msg}")

    # --- TOP ---
    elif sub == "top":
        top = await get_clan_top(10)
        if not top:
            return await message.answer("Кланов пока нет.")
        medals = ["🥇", "🥈", "🥉"]
        text = "🏆 <b>Топ кланов:</b>\n\n"
        for i, c in enumerate(top):
            prefix = medals[i] if i < 3 else f"{i+1}."
            text += f"{prefix} <b>{c['name']}</b> — {c['balance']:.0f} монет ({c['members_count']} чел.)\n"
        await message.answer(text)

    # --- LEAVE ---
    elif sub == "leave":
        success = await leave_clan(uid)
        if success:
            await message.answer("✅ Ты покинул клан.")
        else:
            await message.answer("❌ Ты не состоишь в клане.")

    else:
        await message.answer("Неизвестная команда. Введи /clan для справки.")



async def main():
    global BOT_USERNAME
    await init_db()
    me = await bot.get_me()
    BOT_USERNAME = me.username
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="🏠 Начать / Меню"),
            types.BotCommand(command="play", description="<tg-emoji emoji-id='5467583879948803288'>🎮</tg-emoji> Играть"),
            types.BotCommand(command="profile", description="👤 Профиль"),
            types.BotCommand(command="top", description="<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji> Топ игроков"),
            types.BotCommand(command="history", description="📜 История"),
            types.BotCommand(command="bonus", description="<tg-emoji emoji-id='5235695112419303615'>🎁</tg-emoji> Бонус"),
            types.BotCommand(command="help", description="❓ Помощь"),
        ])
    except Exception:
        pass
    # throttling off
    # throttling off
    logging.info(f"Бот запущен! @{BOT_USERNAME}")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
































