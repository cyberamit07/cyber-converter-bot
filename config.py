"""
Configuration module for the Currency Converter Bot.
Loads environment variables and provides configuration settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Bot Configuration
    bot_token: str = os.getenv("BOT_TOKEN", "")
    
    # API Configuration
    api_timeout: int = int(os.getenv("API_TIMEOUT", "10"))
    cache_ttl: int = int(os.getenv("CACHE_TTL", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # API Endpoints
    coingecko_api: str = "https://api.coingecko.com/api/v3/simple/price"
    ton_api: str = "https://api.tonapi.io/v2/rates"
    exchange_rate_api: str = "https://api.exchangerate-api.com/v4/latest/USD"
    
    # Supported currencies
    supported_currencies: list = ["ton", "usdt", "usd", "inr", "rub", "eur", "star"]
    
    # Rate limits
    rate_limit_seconds: int = 2
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create global settings instance
settings = Settings()

# Validate required settings
if not settings.bot_token:
    raise ValueError("BOT_TOKEN is required in .env file")