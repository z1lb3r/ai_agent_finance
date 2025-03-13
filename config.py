"""
Configuration settings for the Investment AI Agent.
"""

# OpenAI API credentials
OPENAI_API_KEY = "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"

# SEC EDGAR API settings
SEC_EDGAR_USER_AGENT = "InvestmentAIAgent czilber@proton.me"

# Model settings
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.2
MAX_TOKENS = 4000

# Other configuration parameters
REQUEST_TIMEOUT = 30  # Timeout for API requests in seconds
CACHE_EXPIRY = 3600   # Cache expiry time in seconds (1 hour)