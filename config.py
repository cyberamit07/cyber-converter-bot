import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # Bot Configuration
    bot_token: str = os.getenv("BOT_TOKEN", "")
    
    # GetBlock API Key
    getblock_api_key: str = os.getenv("GETBLOCK_API_KEY", "")
    
    # API Configuration
    api_timeout: int = int(os.getenv("API_TIMEOUT", "10"))
    cache_ttl: int = int(os.getenv("CACHE_TTL", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # API Endpoints
    getblock_url: str = "https://api.getblock.io/ton/mainnet"
    coingecko_api: str = "https://api.coingecko.com/api/v3/simple/price"
    exchange_rate_api: str = "https://api.exchangerate-api.com/v4/latest/USD"
    
    # Supported currencies
    supported_currencies: list = ["ton", "usdt", "usd", "inr", "rub", "eur", "star"]
    
    # Rate limits
    rate_limit_seconds: int = 2
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

if not settings.bot_token:
    raise ValueError("BOT_TOKEN is required in .env file")

if not settings.getblock_api_key:
    print("⚠️ Warning: GETBLOCK_API_KEY not set. Using CoinGecko fallback.")