"""
Investment AI Agent - Using OpenAI Agents SDK.

This module implements the investment agent using OpenAI's Agents SDK.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from openai import OpenAI
from agents import Agent, function_tool, set_default_openai_key, set_tracing_disabled
from agents.model_settings import ModelSettings

from config import (
    OPENAI_API_KEY, 
    DEFAULT_MODEL, 
    DEFAULT_TEMPERATURE
)
from prompts.investment_advisor import INVESTMENT_ADVISOR_PROMPT
import tools

# Устанавливаем API-ключ для Agents SDK
set_default_openai_key(OPENAI_API_KEY)

# Отключаем трассировку для устранения возможных ошибок
set_tracing_disabled(True)

# Настраиваем логгер
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("investment_agent")

# Регистрируем инструменты с помощью декоратора function_tool
@function_tool
def get_company_profile(ticker: str) -> str:
    """
    Get a comprehensive profile of a company.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
    """
    try:
        result = tools.get_company_profile(ticker)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_company_profile: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_financial_metrics(ticker: str) -> str:
    """
    Get key financial metrics for a company.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
    """
    try:
        result = tools.get_financial_metrics(ticker)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_financial_metrics: {str(e)}")
        return json.dumps({"error": str(e)})

# Изменяем функцию, удаляя значение по умолчанию
@function_tool
def get_recent_filings_summary(ticker: str, limit: Optional[int] = None) -> str:
    """
    Get a summary of recent SEC filings for a company.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        limit: Maximum number of filings to retrieve
    """
    try:
        # Если limit не указан, используем значение по умолчанию внутри функции
        actual_limit = 5 if limit is None else limit
        result = tools.get_recent_filings_summary(ticker, actual_limit)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_recent_filings_summary: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def compare_companies(tickers: List[str], metrics: Optional[List[str]] = None) -> str:
    """
    Compare multiple companies across specified metrics.
    
    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        metrics: List of metrics to compare
    """
    try:
        result = tools.compare_companies(tickers, metrics)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in compare_companies: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_market_summary() -> str:
    """
    Get a summary of current market conditions.
    """
    try:
        result = tools.get_market_summary()
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_market_summary: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_sector_performance() -> str:
    """
    Get performance data for market sectors.
    """
    try:
        result = tools.get_sector_performance()
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_sector_performance: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_economic_indicators() -> str:
    """
    Get current economic indicators.
    """
    try:
        result = tools.get_economic_indicators()
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_economic_indicators: {str(e)}")
        return json.dumps({"error": str(e)})

# Изменяем функцию, удаляя значение по умолчанию
@function_tool
def get_market_news(limit: Optional[int] = None) -> str:
    """
    Get latest market news.
    
    Args:
        limit: Maximum number of news items to retrieve
    """
    try:
        # Если limit не указан, используем значение по умолчанию внутри функции
        actual_limit = 5 if limit is None else limit
        result = tools.get_market_news(actual_limit)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in get_market_news: {str(e)}")
        return json.dumps({"error": str(e)})

# Создаем настройки модели
model_settings = ModelSettings(temperature=DEFAULT_TEMPERATURE)

# Создаем экземпляр агента
investment_agent = Agent(
    name="InvestmentAdvisor",
    instructions=INVESTMENT_ADVISOR_PROMPT,
    model=DEFAULT_MODEL,
    model_settings=model_settings,
    tools=[
        get_company_profile,
        get_financial_metrics,
        get_recent_filings_summary,
        compare_companies,
        get_market_summary,
        get_sector_performance,
        get_economic_indicators,
        get_market_news
    ]
)

logger.info("Investment Agent created successfully")