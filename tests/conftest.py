import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:1/test"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["MONO_TOKEN_ENCRYPTION_KEY"] = "Y2Ns3VxBa1QHCoGq4fVR6v2yK0O5yS7bR1n0Hk2mL8U="
os.environ["MONO_WEBHOOK_URL"] = "https://example.test/webhook"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["SENTRY_DSN"] = ""
