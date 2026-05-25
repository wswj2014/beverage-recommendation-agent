import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "beverages.db")

MAX_DIALOGUE_TURNS = 10
USER_PROFILE_UPDATE_INTERVAL = 5
