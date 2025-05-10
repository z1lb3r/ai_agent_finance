"""
Configuration settings for the Investment AI Agent.
"""

# OpenAI API credentials
OPENAI_API_KEY = "YOURKEYHERE"

# SEC API settings
SEC_API_KEY = "YOURKEYHERE"  # Замените на ваш ключ API от sec-api.io
SEC_EDGAR_USER_AGENT = "InvestmentAIAgent czilber@proton.me"

# Model settings
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.2
MAX_TOKENS = 4000

# Other configuration parameters
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds
CACHE_EXPIRY = 3600   # Cache expiry time in seconds (1 hour)
