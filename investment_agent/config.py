import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# OpenAI API credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения")

# SEC API settings
SEC_API_KEY = os.getenv("SEC_API_KEY")
if not SEC_API_KEY:
    raise ValueError("SEC_API_KEY не найден в переменных окружения")

SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "InvestmentAIAgent default@example.com")

# Bybit API settings
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")  # Опционально, для приватных методов в будущем
BYBIT_SECRET_KEY = os.getenv("BYBIT_SECRET_KEY")  # Опционально, для приватных методов в будущем
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

# Model settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

# API request parameters
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # Timeout for API requests in seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # Maximum number of retries for API requests
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "1"))  # Initial delay between retries in seconds
RATE_LIMIT_DELAY = int(os.getenv("RATE_LIMIT_DELAY", "5"))  # Delay when hitting rate limits in seconds

# Other configuration parameters
CACHE_EXPIRY = int(os.getenv("CACHE_EXPIRY", "3600"))  # Cache expiry time in seconds (1 hour)

# Дополнительная проверка критически важных переменных
def validate_config():
    """Проверяет, что все критически важные переменные заданы."""
    required_vars = ["OPENAI_API_KEY", "SEC_API_KEY"]
    missing_vars = [var for var in required_vars if not globals().get(var)]
    
    if missing_vars:
        raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
    
    print("✅ Конфигурация проверена успешно")

# Выполняем проверку при импорте модуля
if __name__ != "__main__":
    validate_config()

