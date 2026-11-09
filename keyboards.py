from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def agreement_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="accept_agreement")]
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Играть", callback_data="play")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="🏆 Топ игроков", callback_data="top")
    kb.button(text="📜 История игр", callback_data="history")
    kb.button(text="🎁 Бонус", callback_data="bonus")
    kb.button(text="🎟 Промокод", callback_data="promo")
    kb.button(text="🎁 Подарки", callback_data="gifts")
    kb.button(text="⚔️ Дуэли", callback_data="duels")
    kb.button(text="👑 VIP", callback_data="vip")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Моя ссылка", callback_data="ref_link")
    kb.button(text="👥 Мои рефералы", callback_data="my_refs")
    kb.button(text="📊 Статистика", callback_data="stats")
    kb.button(text="📜 История игр", callback_data="history")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(2, 1, 1, 1, 1)
    return kb.as_markup()


def settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Установить ник", callback_data="setnick_btn")
    kb.button(text="👤 Показывать в топе", callback_data="settops_btn")
    kb.button(text="🗑 Удалить ник", callback_data="clearnick_btn")
    kb.button(text="⬅️ В профиль", callback_data="profile")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def games_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎰 Слоты", callback_data="game_slots")
    kb.button(text="🎲 Кости", callback_data="game_dice")
    kb.button(text="🎯 Дартс", callback_data="game_darts")
    kb.button(text="🏀 Баскетбол", callback_data="game_basketball")
    kb.button(text="⚽️ Футбол", callback_data="game_football")
    kb.button(text="🎳 Боулинг", callback_data="game_bowling")
    kb.button(text="🎡 Рулетка", callback_data="roulette")
    kb.button(text="🎯 Прогноз кубик", callback_data="predict")
    kb.button(text="🏀 Прогноз баскет", callback_data="basket_predict")
    kb.button(text="⚽ Прогноз футбол", callback_data="football_predict")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(2, 2, 2, 2, 1, 1, 1)
    return kb.as_markup()


def play_kb(game: str, last_bet: float = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if last_bet and last_bet > 0:
        kb.button(text=f"🔁 Играть снова ({int(last_bet)})", callback_data=f"play_{game}_{int(last_bet)}")
    kb.button(text="💵 10", callback_data=f"play_{game}_10")
    kb.button(text="💰 50", callback_data=f"play_{game}_50")
    kb.button(text="💎 100", callback_data=f"play_{game}_100")
    kb.button(text="✏️ Своя ставка", callback_data=f"custombet_{game}")
    kb.button(text="💰 Всё", callback_data=f"allin_play_{game}")
    kb.button(text="⬅️ К играм", callback_data="play")
    if last_bet and last_bet > 0:
        kb.adjust(1, 3, 1, 1, 1)
    else:
        kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def history_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="⬅️", callback_data=f"hist_{page - 1}")
    else:
        kb.button(text="⬅️", callback_data="hist_noop")
    if page < total_pages - 1:
        kb.button(text="➡️", callback_data=f"hist_{page + 1}")
    else:
        kb.button(text="➡️", callback_data="hist_noop")
    if total_pages > 1:
        kb.button(text=f"📄 {page + 1}/{total_pages}", callback_data="hist_noop")
    kb.button(text="🏠 В меню", callback_data="menu")
    if total_pages > 1:
        kb.adjust(2, 1, 1)
    else:
        kb.adjust(2, 1)
    return kb.as_markup()


def roulette_bet_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔴 Красное (x2)", callback_data="roul_color_red")
    kb.button(text="⚫ Чёрное (x2)", callback_data="roul_color_black")
    kb.button(text="🟢 Зеро (x14)", callback_data="roul_color_green")
    kb.button(text="🎲 Точное число (x36)", callback_data="roul_number")
    kb.button(text="⬅️ К играм", callback_data="play")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def roulette_amount_kb(bet_type: str, bet_value: str = "", last_bet: float = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    suffix = bet_type
    if bet_value:
        suffix += f"_{bet_value}"
    if last_bet and last_bet > 0:
        kb.button(text=f"🔁 Снова ({int(last_bet)})", callback_data=f"roulbet_{suffix}_{int(last_bet)}")
    kb.button(text="💵 10", callback_data=f"roulbet_{suffix}_10")
    kb.button(text="💰 50", callback_data=f"roulbet_{suffix}_50")
    kb.button(text="💎 100", callback_data=f"roulbet_{suffix}_100")
    kb.button(text="✏️ Своя ставка", callback_data=f"roulcustom_{suffix}")
    kb.button(text="💰 Всё", callback_data=f"allin_roulbet_{suffix}")
    kb.button(text="⬅️ Назад", callback_data="roulette")
    if last_bet and last_bet > 0:
        kb.adjust(1, 3, 1, 1, 1)
    else:
        kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def roulette_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="roulette")]
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu")]
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ])


def profile_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Профиль", callback_data="profile")]
    ])


def promo_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu")]
    ])


def top_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="⬅️", callback_data=f"top_{page - 1}")
    if total_pages > 1:
        kb.button(text=f"📄 {page + 1}/{total_pages}", callback_data="top_noop")
    if page < total_pages - 1:
        kb.button(text="➡️", callback_data=f"top_{page + 1}")
    kb.button(text="🏠 В меню", callback_data="menu")
    if total_pages > 1:
        kb.adjust(2, 1)
    else:
        kb.adjust(1)
    return kb.as_markup()


def refs_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Моя ссылка", callback_data="ref_link")
    kb.button(text="⬅️ В профиль", callback_data="profile")
    kb.adjust(1)
    return kb.as_markup()


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_reply_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🎮 Играть")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📜 История")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="🏠 Меню")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие..."
    )
    return kb


def predict_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Чёт (x1.9)", callback_data="pred_even")
    kb.button(text="🎲 Нечет (x1.9)", callback_data="pred_odd")
    kb.button(text="⬆️ Больше 3 (x1.9)", callback_data="pred_high")
    kb.button(text="⬇️ Меньше 4 (x1.9)", callback_data="pred_low")
    kb.button(text="🎯 Точное число (x5)", callback_data="pred_exact")
    kb.button(text="⬅️ К играм", callback_data="play")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def predict_amount_kb(ptype: str = "", val: str = "", last_bet: float = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    suffix = ptype
    if val:
        suffix += f"_{val}"
    if last_bet and last_bet > 0:
        kb.button(text=f"🔁 Снова ({int(last_bet)})", callback_data=f"predbet_{suffix}_{int(last_bet)}")
    kb.button(text="💵 10", callback_data=f"predbet_{suffix}_10")
    kb.button(text="💰 50", callback_data=f"predbet_{suffix}_50")
    kb.button(text="💎 100", callback_data=f"predbet_{suffix}_100")
    kb.button(text="✏️ Своя ставка", callback_data=f"predcustom_{suffix}")
    kb.button(text="💰 Всё", callback_data=f"allin_predbet_{suffix}")
    kb.button(text="⬅️ Назад", callback_data="predict")
    if last_bet and last_bet > 0:
        kb.adjust(1, 3, 1, 1, 1)
    else:
        kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def predict_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="predict")]
    ])


def basket_predict_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏀 Забьёт (x2.5)", callback_data="bpred_hit")
    kb.button(text="🔔 Застрянет (x7)", callback_data="bpred_stuck")
    kb.button(text="❌ Не забьёт (x2)", callback_data="bpred_miss")
    kb.button(text="⬅️ К играм", callback_data="play")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def basket_amount_kb(ptype: str, last_bet: float = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if last_bet and last_bet > 0:
        kb.button(text=f"🔁 Снова ({int(last_bet)})", callback_data=f"bpredbet_{ptype}_{int(last_bet)}")
    kb.button(text="💵 10", callback_data=f"bpredbet_{ptype}_10")
    kb.button(text="💰 50", callback_data=f"bpredbet_{ptype}_50")
    kb.button(text="💎 100", callback_data=f"bpredbet_{ptype}_100")
    kb.button(text="✏️ Своя ставка", callback_data=f"bpredcustom_{ptype}")
    kb.button(text="💰 Всё", callback_data=f"allin_bpredbet_{ptype}")
    kb.button(text="⬅️ Назад", callback_data="basket_predict")
    if last_bet and last_bet > 0:
        kb.adjust(1, 3, 1, 1, 1)
    else:
        kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def football_predict_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚽ Гол (x2)", callback_data="fpred_goal")
    kb.button(text="🥅 Штанга (x7)", callback_data="fpred_post")
    kb.button(text="❌ Мимо (x2.5)", callback_data="fpred_miss")
    kb.button(text="⬅️ К играм", callback_data="play")
    kb.adjust(1)
    return kb.as_markup()


def football_amount_kb(ptype: str, last_bet: float = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if last_bet and last_bet > 0:
        kb.button(text=f"🔁 Снова ({int(last_bet)})", callback_data=f"fpredbet_{ptype}_{int(last_bet)}")
    kb.button(text="💵 10", callback_data=f"fpredbet_{ptype}_10")
    kb.button(text="💰 50", callback_data=f"fpredbet_{ptype}_50")
    kb.button(text="💎 100", callback_data=f"fpredbet_{ptype}_100")
    kb.button(text="✏️ Своя ставка", callback_data=f"fpredcustom_{ptype}")
    kb.button(text="💰 Всё", callback_data=f"allin_fpredbet_{ptype}")
    kb.button(text="⬅️ Назад", callback_data="football_predict")
    if last_bet and last_bet > 0:
        kb.adjust(1, 3, 1, 1, 1)
    else:
        kb.adjust(3, 1, 1, 1)
    return kb.as_markup()


def gifts_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Подарить монеты", callback_data="gift_send")
    kb.button(text="📥 Полученные", callback_data="gift_received")
    kb.button(text="📤 Отправленные", callback_data="gift_sent")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def gift_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="gifts")]
    ])


def duels_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Создать дуэль", callback_data="duel_create")
    kb.button(text="📜 Мои дуэли", callback_data="duel_history")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def duel_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="duels")]
    ])



def basket_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="basket_predict")]
    ])


def football_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="football_predict")]
    ])


HELP_PAGES = [
    (
        "🌟 <b>Помощь (1/3)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🎮 Игры:</b>\n"
        "🎰 Слоты · "
        "🎲 Кости · "
        "🎯 Дартс\n"
        "🏀 Баскет · "
        "⚽️ Футбол · "
        "🎳 Боулинг\n"
        "📱 Рулетка\n\n"
        "<b>🎯 Прогнозы:</b>\n"
        "🎲 Кубик — чёт/нечет/точное число\n"
        "🏀 Баскет — забьёт/застрянет/мимо\n"
        "⚽️ Футбол — гол/штанга/мимо\n\n"
        "💡 Выбери игру → ставку → смотри результат."
    ),
    (
        "🌟 <b>Помощь (2/3)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🎁 Подарки</b>\n"
        "Передай монеты другому игроку по ID\n\n"
        "<b>⚔️ Дуэли</b>\n"
        "Бросок монетки 50/50 с другом\n\n"
        "<b>🏆 Достижения</b>\n"
        "10 значков за активность\n\n"
        "<b>🤩 Рефералка</b>\n"
        "💵 +1300 монет за каждого друга\n\n"
        "<b>👑 VIP</b>\n"
        "Silver (120к) и Gold (600к)\nБонус: Silver 1900 / 1ч50м, Gold 3500 / 1ч\n"
        "Дают бонусы к выигрышу"
    ),
    (
        "🌟 <b>Помощь (3/3)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>💎 Джекпот</b>\n"
        "• 3% с каждой ставки → в банк\n"
        "• Сорвать: выигрыш ×10+ (шанс 1/100)\n"
        "• После срыва сброс до 1000 монет\n\n"
        "<b>🎁 Бонус</b> — 700 монет раз в 3 часа\n"
        "<b>🎟️ Промокод</b> — коды от админа\n"
        "<b>📈 Статистика</b> — подробно по играм\n"
        "<b>📝 История</b> — последние ставки\n"
        "<b>🏆 Топ игроков</b> — топ-100\n\n"
        "🎼 <b>Связь с админом:</b> @Nonsi11"
    ),
]


def help_kb(page: int, total: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="⬅️", callback_data=f"help_{page - 1}")
    else:
        kb.button(text="⬅️", callback_data="help_noop")
    if page < total - 1:
        kb.button(text="➡️", callback_data=f"help_{page + 1}")
    else:
        kb.button(text="➡️", callback_data="help_noop")
    if total > 1:
        kb.button(text=f"📄 {page + 1}/{total}", callback_data="help_noop")
    kb.button(text="🏠 В меню", callback_data="menu")
    if total > 1:
        kb.adjust(2, 1, 1)
    else:
        kb.adjust(2, 1)
    return kb.as_markup()


def vip_menu_kb(current_level: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if current_level < 1:
        kb.button(text="🥈 Купить Silver", callback_data="vip_buy_1")
    if current_level < 2:
        kb.button(text="👑 Купить Gold", callback_data="vip_buy_2")
    kb.button(text="📊 Мой статус", callback_data="vip_my")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def vip_confirm_kb(level: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, купить", callback_data=f"vip_confirm_{level}")
    kb.button(text="❌ Отмена", callback_data="vip")
    kb.adjust(1)
    return kb.as_markup()


def duel_side_kb(code: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🦅 Орёл", callback_data=f"duelside_eagle_{code}")
    kb.button(text="🌟 Решка", callback_data=f"duelside_star_{code}")
    kb.adjust(2)
    return kb.as_markup()
