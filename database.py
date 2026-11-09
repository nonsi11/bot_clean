import aiosqlite
import time
from config import DB_NAME


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                agreed INTEGER NOT NULL DEFAULT 0,
                balance REAL NOT NULL DEFAULT 0.0,
                total_bets INTEGER NOT NULL DEFAULT 0,
                total_wins INTEGER NOT NULL DEFAULT 0,
                total_loses INTEGER NOT NULL DEFAULT 0,
                total_wagered REAL NOT NULL DEFAULT 0.0,
                referred_by INTEGER,
                last_bonus INTEGER NOT NULL DEFAULT 0,
                last_bet REAL NOT NULL DEFAULT 0.0,
                created_at INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                uses_left INTEGER NOT NULL,
                created_by INTEGER,
                created_at INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                used_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (code, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bet_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                bet REAL NOT NULL,
                result INTEGER NOT NULL,
                win REAL NOT NULL,
                created_at INTEGER NOT NULL DEFAULT 0
            )
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_bet REAL NOT NULL DEFAULT 0.0")
        except Exception:
            pass
        await db.commit()


async def ensure_user(user_id, username=None):
    async with aiosqlite.connect(DB_NAME) as db:
        now = int(time.time())
        await db.execute("""
            INSERT INTO users (user_id, username, created_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
        """, (user_id, username, now))
        await db.commit()
    try:
        await apply_tax(user_id)
    except Exception:
        pass


async def set_agreed(user_id, username=None):
    async with aiosqlite.connect(DB_NAME) as db:
        now = int(time.time())
        await db.execute("""
            INSERT INTO users (user_id, username, agreed, created_at) VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET agreed = 1, username = excluded.username
        """, (user_id, username, now))
        await db.commit()


async def is_agreed(user_id) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT agreed FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0] == 1)


async def get_balance(user_id) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return float(row[0]) if row else 0.0


async def update_balance(user_id, delta):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()


async def add_bet_stats(user_id, bet, win):
    async with aiosqlite.connect(DB_NAME) as db:
        won = 1 if win > 0 else 0
        lost = 1 if win == 0 else 0
        await db.execute("""
            UPDATE users SET
                total_bets = total_bets + 1,
                total_wins = total_wins + ?,
                total_loses = total_loses + ?,
                total_wagered = total_wagered + ?
            WHERE user_id = ?
        """, (won, lost, bet, user_id))
        await db.commit()


async def add_history(user_id, game, bet, result, win):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO bet_history (user_id, game, bet, result, win, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, game, bet, result, win, int(time.time())))
        await db.commit()


async def get_history(user_id, limit=5, offset=0):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM bet_history WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (user_id, limit, offset)) as cur:
            return await cur.fetchall()


async def get_history_count(user_id) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM bet_history WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def get_top_players(limit=10, offset=0):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, username, balance, nick, show_nick FROM users
            WHERE agreed = 1
            ORDER BY balance DESC LIMIT ? OFFSET ?
        """, (limit, offset)) as cur:
            return await cur.fetchall()


async def set_referrer(user_id, referrer_id):
    if user_id == referrer_id:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0] is not None:
                return False
        await db.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
        await db.commit()
        return True


async def get_referrals_count(user_id) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def get_last_bonus(user_id) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] else 0


async def set_last_bonus(user_id, ts):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (ts, user_id))
        await db.commit()


async def get_last_bet(user_id) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT last_bet FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return float(row[0]) if row and row[0] else 0.0


async def set_last_bet(user_id, bet):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_bet = ? WHERE user_id = ?", (bet, user_id))
        await db.commit()


async def create_promo(code, amount, uses, created_by):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("""
                INSERT INTO promo_codes (code, amount, uses_left, created_by, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (code.upper(), amount, uses, created_by, int(time.time())))
            # Чистим старые следы использования (если код был раньше)
            await db.execute("DELETE FROM promo_uses WHERE code = ?", (code.upper(),))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def delete_promo(code):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("DELETE FROM promo_codes WHERE code = ?", (code.upper(),))
        await db.execute("DELETE FROM promo_uses WHERE code = ?", (code.upper(),))
        await db.commit()
        return cur.rowcount > 0


async def list_promos():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC") as cur:
            return await cur.fetchall()


async def use_promo(code, user_id):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM promo_codes WHERE code = ?", (code,)) as c:
            promo = await c.fetchone()
        if not promo or promo["uses_left"] <= 0:
            return False
        async with conn.execute("SELECT 1 FROM promo_uses WHERE code = ? AND user_id = ?", (code, user_id)) as c:
            if await c.fetchone():
                return False
        await conn.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?", (code,))
        await conn.execute("INSERT INTO promo_uses (code, user_id, used_at) VALUES (?, ?, ?)", (code, user_id, int(time.time())))
        await conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (promo["amount"], user_id))
        await conn.commit()
        return True

async def get_referrals_list(user_id, limit=20):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, username, balance, nick, show_nick FROM users
            WHERE referred_by = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


async def add_gift(sender_id, receiver_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO gifts (sender_id, receiver_id, amount, created_at) VALUES (?, ?, ?, ?)",
            (sender_id, receiver_id, amount, int(time.time()))
        )
        await db.commit()


async def get_gifts_received(user_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT g.*, u.username as sender_name FROM gifts g
            LEFT JOIN users u ON u.user_id = g.sender_id
            WHERE g.receiver_id = ?
            ORDER BY g.created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


async def get_gifts_sent(user_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT g.*, u.username as receiver_name FROM gifts g
            LEFT JOIN users u ON u.user_id = g.receiver_id
            WHERE g.sender_id = ?
            ORDER BY g.created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


async def find_user_by_id(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()


async def get_jackpot():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT amount FROM jackpot WHERE id = 1") as cur:
            row = await cur.fetchone()
            return float(row[0]) if row else 0.0


async def add_to_jackpot(amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE jackpot SET amount = amount + ? WHERE id = 1", (amount,))
        await db.commit()


async def claim_jackpot():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT amount FROM jackpot WHERE id = 1") as cur:
            row = await cur.fetchone()
            amount = float(row[0]) if row else 0.0
        await db.execute("UPDATE jackpot SET amount = 1000 WHERE id = 1")
        await db.commit()
        return amount


# Список всех достижений: (id, эмодзи, название, описание)
ACHIEVEMENTS = [
    ("first_bet", "<tg-emoji emoji-id='5256131095094652290'>🎯</tg-emoji>", "Первый шаг", "Сделать первую ставку"),
    ("wins_10", "<tg-emoji emoji-id='5276032951342088188'>💥</tg-emoji>", "В ударе", "10 побед"),
    ("wins_100", "<tg-emoji emoji-id='5278487963238413806'>💪</tg-emoji>", "Опытный", "100 побед"),
    ("bets_100", "<tg-emoji emoji-id='5796536533251007149'>🎰</tg-emoji>", "Азартный", "100 ставок"),
    ("bets_1000", "<tg-emoji emoji-id='5188344996356448758'>🏆</tg-emoji>", "Мастер", "1000 ставок"),
    ("rich_10k", "<tg-emoji emoji-id='5409048419211682843'>💵</tg-emoji>", "Богач", "Накопить 10 000 монет"),
    ("rich_1m", "<tg-emoji emoji-id='5427168083074628963'>💎</tg-emoji>", "Миллионер", "Накопить 1 000 000 монет"),
    ("referral_1", "<tg-emoji emoji-id='5318809068968638535'>🤩</tg-emoji>", "Друг", "Пригласить друга"),
    ("referral_10", "<tg-emoji emoji-id='5294494498896756050'>👑</tg-emoji>", "Популярный", "Пригласить 10 друзей"),
    ("jackpot", "<tg-emoji emoji-id='5461151367559141950'>🎉</tg-emoji>", "Счастливчик", "Сорвать джекпот"),
]


async def has_achievement(user_id, ach_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM achievements WHERE user_id = ? AND achievement = ?",
            (user_id, ach_id)
        ) as cur:
            return await cur.fetchone() is not None


async def unlock_achievement(user_id, ach_id):
    """Возвращает True, если достижение новое (только что открыто)."""
    if await has_achievement(user_id, ach_id):
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO achievements (user_id, achievement, unlocked_at) VALUES (?, ?, ?)",
            (user_id, ach_id, int(time.time()))
        )
        await db.commit()
    return True


async def get_user_achievements(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT achievement FROM achievements WHERE user_id = ?",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


import random as _random
import string as _string


def generate_duel_code():
    return ''.join(_random.choices(_string.ascii_uppercase + _string.digits, k=6))


async def create_duel(creator_id, amount):
    code = generate_duel_code()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO duels (code, creator_id, amount, status, created_at) VALUES (?, ?, ?, 'waiting', ?)",
            (code, creator_id, amount, int(time.time()))
        )
        await db.commit()
    return code


async def get_duel(code):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM duels WHERE code = ?", (code,)) as cur:
            return await cur.fetchone()


async def join_duel(code, opponent_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM duels WHERE code = ?", (code,)) as cur:
            duel = await cur.fetchone()
        if not duel or duel["status"] != "waiting":
            return None
        await db.execute(
            "UPDATE duels SET opponent_id = ?, status = 'active' WHERE code = ?",
            (opponent_id, code)
        )
        await db.commit()
        return duel


async def finish_duel(code, winner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE duels SET status = 'finished', winner_id = ? WHERE code = ?",
            (winner_id, code)
        )
        await db.commit()


async def cancel_duel(code):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE duels SET status = 'cancelled' WHERE code = ?", (code,))
        await db.commit()


async def get_user_duels(user_id, limit=5):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM duels
            WHERE (creator_id = ? OR opponent_id = ?) AND status = 'finished'
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, user_id, limit)) as cur:
            return await cur.fetchall()


async def get_game_stats(user_id):
    """Статистика по играм: (game, count, wins, total_bet, total_win)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT game, COUNT(*),
                   SUM(CASE WHEN win > 0 THEN 1 ELSE 0 END),
                   SUM(bet), SUM(win)
            FROM bet_history WHERE user_id = ?
            GROUP BY game
            ORDER BY COUNT(*) DESC
        """, (user_id,)) as cur:
            return await cur.fetchall()


async def get_total_stats(user_id):
    """Общая статистика: (total_bets, total_wins, total_bet_sum, total_win_sum)."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN win > 0 THEN 1 ELSE 0 END),
                   SUM(bet), SUM(win)
            FROM bet_history WHERE user_id = ?
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            return row if row else (0, 0, 0, 0)


async def is_banned(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0] == 1)


async def set_banned(user_id, banned=True):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
        await db.commit()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE agreed = 1 AND banned = 0") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def bot_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE agreed = 1") as c:
            users = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(*) FROM bet_history") as c:
            bets = (await c.fetchone())[0] or 0
        async with db.execute("SELECT SUM(bet) FROM bet_history") as c:
            wagered = (await c.fetchone())[0] or 0
        async with db.execute("SELECT SUM(win) FROM bet_history") as c:
            won = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(*) FROM promo_codes") as c:
            promos = (await c.fetchone())[0] or 0
        async with db.execute("SELECT amount FROM jackpot WHERE id = 1") as c:
            row = await c.fetchone()
            jackpot = float(row[0]) if row else 0
        return {
            "users": users, "bets": bets, "wagered": wagered,
            "won": won, "promos": promos, "jackpot": jackpot,
        }


VIP_PRICES = {
    1: 120_000,
    2: 600_000,
}

VIP_MULTIPLIER = {
    0: 1.0,
    1: 1.05,
    2: 1.10,
}

VIP_BONUS = {
    0: 700,
    1: 1900,
    2: 3500,
}

VIP_COOLDOWN = {
    0: 10800,   # 3 часа
    1: 6600,    # 1 час 50 минут
    2: 3600,    # 1 час
}

VIP_NAMES = {
    0: "Без VIP",
    1: "Silver",
    2: "Gold",
}


async def get_vip(user_id) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT vip_level FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] else 0


async def set_vip(user_id, level):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET vip_level = ? WHERE user_id = ?", (level, user_id))
        await db.commit()


async def cleanup_old_history(keep_per_user=30):
    """Удаляет старые ставки, оставляя последние N на пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
            DELETE FROM bet_history
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id, user_id,
                           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
                    FROM bet_history
                ) WHERE rn <= ?
            )
        """, (keep_per_user,))
        deleted = cur.rowcount
        await db.commit()
        return deleted


async def set_duel_rolls(code, p1_roll, p2_roll, cube_winner):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE duels SET p1_roll = ?, p2_roll = ?, cube_winner = ? WHERE code = ?",
            (p1_roll, p2_roll, cube_winner, code)
        )
        await db.commit()


async def set_duel_side(code, side):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE duels SET chosen_side = ? WHERE code = ?", (side, code))
        await db.commit()


# ============ НАЛОГ НА БОГАТЫХ ============
TAX_THRESHOLD = 450000
TAX_PERCENT = 0.05
TAX_PERIOD = 3 * 24 * 60 * 60  # 3 дня в секундах


async def apply_tax(user_id):
    """Списывает 5% каждые 3 дня, если баланс > 450к и нет иммунитета. Сгорает."""
    async with aiosqlite.connect(DB_NAME) as db:
        now = int(time.time())
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT balance, last_tax, tax_immune_until FROM users WHERE user_id = ?",
            (user_id,)
        ) as c:
            row = await c.fetchone()
        if not row:
            return 0
        if row["tax_immune_until"] and row["tax_immune_until"] > now:
            return 0
        if row["balance"] <= TAX_THRESHOLD:
            return 0
        if row["last_tax"] and (now - row["last_tax"]) < TAX_PERIOD:
            return 0
        tax = row["balance"] * TAX_PERCENT
        new_bal = row["balance"] - tax
        await db.execute(
            "UPDATE users SET balance = ?, last_tax = ? WHERE user_id = ?",
            (new_bal, now, user_id)
        )
        await db.commit()
        return tax


async def set_tax_immune(user_id, until_ts):
    """Устанавливает иммунитет до until_ts (0 = снять)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET tax_immune_until = ? WHERE user_id = ?",
            (until_ts, user_id)
        )
        await db.commit()


async def set_nick(user_id, nick):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET nick = ? WHERE user_id = ?", (nick, user_id))
        await db.commit()


async def clear_nick(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET nick = NULL WHERE user_id = ?", (user_id,))
        await db.commit()


async def set_show_nick(user_id, show):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET show_nick = ? WHERE user_id = ?", (int(show), user_id))
        await db.commit()

# ============ КЛАНЫ ============
async def create_clan(name, owner_id):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            now = int(time.time())
            await db.execute("INSERT INTO clans (name, owner_id, created_at) VALUES (?, ?, ?)", (name, owner_id, now))
            await db.commit()
            async with db.execute("SELECT id FROM clans WHERE name = ?", (name,)) as c:
                row = await c.fetchone()
                clan_id = row[0]
            await db.execute("INSERT INTO clan_members (clan_id, user_id, joined_at) VALUES (?, ?, ?)", (clan_id, owner_id, now))
            await db.commit()
            return True
        except Exception:
            return False


async def get_clan_by_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.* FROM clans c
            JOIN clan_members m ON c.id = m.clan_id
            WHERE m.user_id = ?
        """, (user_id,)) as c:
            return await c.fetchone()


async def get_clan_by_name(name):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM clans WHERE name = ?", (name,)) as c:
            return await c.fetchone()


async def get_clan_members(clan_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.user_id, u.username, u.balance 
            FROM clan_members m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.clan_id = ?
        """, (clan_id,)) as c:
            return await c.fetchall()


async def leave_clan(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
        if not row:
            return False
        clan_id = row[0]
        
        # Проверяем, является ли он владельцем
        async with db.execute("SELECT owner_id FROM clans WHERE id = ?", (clan_id,)) as c:
            owner = (await c.fetchone())[0]
            
        if owner == user_id:
            # Если владелец уходит, клан распускается
            await db.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan_id,))
            await db.execute("DELETE FROM clans WHERE id = ?", (clan_id,))
        else:
            await db.execute("DELETE FROM clan_members WHERE user_id = ?", (user_id,))
        await db.commit()
        return True


async def get_clan_top(limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.name, c.balance, COUNT(m.user_id) as members_count
            FROM clans c
            LEFT JOIN clan_members m ON c.id = m.clan_id
            GROUP BY c.id
            ORDER BY c.balance DESC, members_count DESC
            LIMIT ?
        """, (limit,)) as c:
            return await c.fetchall()



async def deposit_clan(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as conn:
        # Проверяем, в клане ли он
        async with conn.execute("SELECT clan_id FROM clan_members WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
        if not row:
            return False, "Ты не состоишь в клане."
        
        clan_id = row[0]
        
        # Проверяем баланс
        async with conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            bal = (await c.fetchone())[0]
            
        if bal < amount:
            return False, "Недостаточно монет."
            
        # Списываем у юзера, добавляем в казну
        await conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        await conn.execute("UPDATE clans SET balance = balance + ? WHERE id = ?", (amount, clan_id))
        await conn.commit()
        return True, "Успешно"
