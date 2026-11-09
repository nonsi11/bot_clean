import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = "casino.db"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
BONUS_COOLDOWN = 10800
BONUS_AMOUNT = 700
REFERRAL_BONUS = 1300
