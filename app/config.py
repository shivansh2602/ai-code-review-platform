import os

from dotenv import load_dotenv

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://reviewer:devpassword@localhost:5432/reviews",
)