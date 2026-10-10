"""Sozlamalar: .env fayldan o'qiladi."""
import os
from datetime import timedelta, timezone

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "bot.db")
MINIAPP_URL = os.getenv("MINIAPP_URL", "")  # Telegram Mini App uchun HTTPS URL

# Ixtiyoriy sozlamalar
CSFLOAT_KEY = os.getenv("CSFLOAT_API_KEY", "")      # CSFloat narxlari uchun
ADMIN_ID = _int("ADMIN_ID")                          # /stats faqat shu odamga
CHANNEL_ID = os.getenv("CHANNEL_ID", "")             # masalan @mening_kanalim
CHANNEL_LANG = os.getenv("CHANNEL_LANG", "uz")       # uz / ru / en
CHANNEL_POST_HOURS = max(1, _int("CHANNEL_POST_HOURS", 6))

# Umumiy konstantalar
REFRESH_SECONDS = 300          # Skinport limiti: 5 daqiqada 8 so'rov
MAX_ALERTS_PER_USER = 20
MAX_FAVORITES = 50
PLATFORM_FEE_PERCENT = float(os.getenv("PLATFORM_FEE_PERCENT", "5"))
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
PAGE_SIZE = 8
KEY_PRICE = 2.49               # CS2 keys kaliti narxi (USD), taxminiy
DIGEST_HOUR = 9                # Kunlik xabar vaqti (Toshkent)
UZ_TZ = timezone(timedelta(hours=5))
