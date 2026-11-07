import os

from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://reviewer:devpassword@localhost:5432/reviews",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")