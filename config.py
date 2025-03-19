"""
Configuration settings for the Investment AI Agent.
"""

# OpenAI API credentials
OPENAI_API_KEY = "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"

# SEC API settings
SEC_API_KEY = "6a94d5a10de9ab9c28373bde1cae0da653409f10b71d71d44f31cae0ccdc124f"  # Замените на ваш ключ API от sec-api.io
SEC_EDGAR_USER_AGENT = "InvestmentAIAgent czilber@proton.me"

# Model settings
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.2
MAX_TOKENS = 4000

# API request parameters
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for API requests
RETRY_DELAY = 1  # Initial delay between retries in seconds
RATE_LIMIT_DELAY = 5  # Delay when hitting rate limits in seconds

# Other configuration parameters
CACHE_EXPIRY = 3600   # Cache expiry time in seconds (1 hour)