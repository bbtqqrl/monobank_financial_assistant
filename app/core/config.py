import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

MONO_TOKEN_ENCRYPTION_KEY = os.getenv("MONO_TOKEN_ENCRYPTION_KEY")

MONO_WEBHOOK_VERIFY_SIGNATURE = os.getenv("MONO_WEBHOOK_VERIFY_SIGNATURE", "true").lower() == "true"

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
if not MONO_TOKEN_ENCRYPTION_KEY:
    raise RuntimeError("MONO_TOKEN_ENCRYPTION_KEY environment variable is not set")
