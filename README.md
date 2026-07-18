# Currency Converter Telegram Bot

A high-performance Telegram bot that automatically detects and converts currency messages in groups.

## Features

- 🚀 **Instant Detection**: Automatically detects currency messages without commands
- 💱 **Multiple Currencies**: Supports TON, USDT, USD, INR, RUB, EUR, and Telegram Stars
- 🔄 **Real-time Rates**: Fetches live exchange rates with 30-second caching
- 🛡️ **Spam Protection**: Rate limiting and duplicate request prevention
- 📊 **Beautiful Output**: Formatted with emojis for easy reading
- ⚡ **High Performance**: Handles 100,000+ messages per day
- 🔌 **Multiple APIs**: Auto-fallback between CoinGecko, TON API, and ExchangeRate API

## Installation

### Termux (Android)

```bash
# Update packages
pkg update && pkg upgrade

# Install Python
pkg install python python-pip git

# Clone repository
git clone https://github.com/yourusername/currency-bot.git
cd currency-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "BOT_TOKEN=YOUR_BOT_TOKEN_HERE" > .env

# Run the bot
python main.py