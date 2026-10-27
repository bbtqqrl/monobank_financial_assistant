import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

MONO_TOKEN_ENCRYPTION_KEY = os.getenv("MONO_TOKEN_ENCRYPTION_KEY")

MONO_WEBHOOK_URL = os.getenv("MONO_WEBHOOK_URL")
MONO_WEBHOOK_VERIFY_SIGNATURE = os.getenv("MONO_WEBHOOK_VERIFY_SIGNATURE", "true").lower() == "true"

# Optional: when unset, categorization falls back to MockCategorizationAIClient.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ASSISTANT_MODEL = os.getenv("ASSISTANT_MODEL", "claude-haiku-5-5")
ASSISTANT_MAX_TOKENS = int(os.getenv("ASSISTANT_MAX_TOKENS", "8192"))
ASSISTANT_EFFORT = os.getenv("ASSISTANT_EFFORT", "medium")
# TODO: повернути true, коли в застосунку з'являться картки підтвердження дій
ASSISTANT_ACTIONS_NEED_CONFIRMATION = os.getenv("ASSISTANT_ACTIONS_NEED_CONFIRMATION", "false") == "true"
ASSISTANT_DAILY_MESSAGE_LIMIT = int(os.getenv("ASSISTANT_DAILY_MESSAGE_LIMIT", "50"))
ASSISTANT_REPLY_TIMEOUT_SECONDS = int(os.getenv("ASSISTANT_REPLY_TIMEOUT_SECONDS", "90"))
ASSISTANT_COMPACTION_TRIGGER_TOKENS = int(os.getenv("ASSISTANT_COMPACTION_TRIGGER_TOKENS", "60000"))

APPLE_MAPS_TEAM_ID = os.getenv("APPLE_MAPS_TEAM_ID")
APPLE_MAPS_KEY_ID = os.getenv("APPLE_MAPS_KEY_ID")
APPLE_MAPS_PRIVATE_KEY = os.getenv("APPLE_MAPS_PRIVATE_KEY", "").replace("\\n", "\n")
# TODO: прибрати, коли на сервері буде .p8 ключ Apple Maps
APPLE_MAPS_TOKEN = os.getenv("APPLE_MAPS_TOKEN")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACE_SEARCH_RADIUS_M = int(os.getenv("PLACE_SEARCH_RADIUS_M", "30"))
PLACES_COMPARE_LOG = os.getenv("PLACES_COMPARE_LOG")

EXPO_ACCESS_TOKEN = os.getenv("EXPO_ACCESS_TOKEN")

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "production")
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
if not MONO_TOKEN_ENCRYPTION_KEY:
    raise RuntimeError("MONO_TOKEN_ENCRYPTION_KEY environment variable is not set")
if not MONO_WEBHOOK_URL:
    raise RuntimeError("MONO_WEBHOOK_URL environment variable is not set")
