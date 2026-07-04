import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_CHAT_ID = os.getenv("FEISHU_CHAT_ID", "")
    FEISHU_TOKEN_EXPIRE_MINUTES = int(os.getenv("FEISHU_TOKEN_EXPIRE_MINUTES", 110))
    FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/momentum_strategy.db")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/app.log")
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", 10485760))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))

    MOMENTUM_PERIOD = int(os.getenv("MOMENTUM_PERIOD", 20))
    TOP_N = int(os.getenv("TOP_N", 5))
    USE_EWMA = os.getenv("USE_EWMA", "false").lower() == "true"
    EWMA_ALPHA = float(os.getenv("EWMA_ALPHA", 0.1))

    PRICE_CHANGE_THRESHOLD = float(os.getenv("PRICE_CHANGE_THRESHOLD", 30))
    MIN_VOLUME_20D = int(os.getenv("MIN_VOLUME_20D", 1000000))
    MIN_VOLUME_AMOUNT = float(os.getenv("MIN_VOLUME_AMOUNT", 5000000))

    PIPELINE_TIME = os.getenv("PIPELINE_TIME", "16:00")
    TOKEN_REFRESH_INTERVAL = int(os.getenv("TOKEN_REFRESH_INTERVAL", 7200))

    PUSH_MODE = os.getenv("PUSH_MODE", "card")
    PUSH_FREQUENCY = os.getenv("PUSH_FREQUENCY", "daily")

    REQUEST_INTERVAL = float(os.getenv("REQUEST_INTERVAL", 1))
    MAX_RETRY = int(os.getenv("MAX_RETRY", 3))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", 10))


config = Config()
