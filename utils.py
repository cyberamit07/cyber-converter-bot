"""
Utility functions for the Currency Converter Bot.
"""

import logging
from typing import Optional
from datetime import datetime

def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def format_time(timestamp: float) -> str:
    """
    Format a timestamp to readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted time string
    """
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def sanitize_message(text: str) -> str:
    """
    Sanitize message text to prevent injection attacks.
    
    Args:
        text: Raw message text
        
    Returns:
        Sanitized text
    """
    # Remove any potential harmful characters
    return text.strip()[:1000]  # Limit length

def is_private_chat(chat_type: str) -> bool:
    """
    Check if a chat is private.
    
    Args:
        chat_type: Telegram chat type
        
    Returns:
        True if private chat
    """
    return chat_type == "private"