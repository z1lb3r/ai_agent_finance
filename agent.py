"""
Investment AI Agent - Using OpenAI Agents SDK.

This module implements the investment agent using OpenAI's Agents SDK,
with focus on SEC filing download and analysis functionality.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime

from openai import OpenAI
from agents import Agent, set_default_openai_key, set_tracing_disabled
from agents.model_settings import ModelSettings

from config import (
    OPENAI_API_KEY, 
    DEFAULT_MODEL, 
    DEFAULT_TEMPERATURE
)
from prompts.investment_advisor import INVESTMENT_ADVISOR_PROMPT

# Импортируем наш реестр инструментов
from tools.registry import get_all_tools

# Устанавливаем API-ключ для Agents SDK
set_default_openai_key(OPENAI_API_KEY)

# Отключаем трассировку для устранения возможных ошибок
set_tracing_disabled(True)

# Настраиваем логгер
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("investment_agent")

# Создаем настройки модели
model_settings = ModelSettings(temperature=DEFAULT_TEMPERATURE)

# Объявляем переменную для агента
investment_agent = None

def initialize_agent():
    """
    Инициализирует агента с инструментами из реестра.
    
    Returns:
        Agent: Инициализированный агент
    """
    global investment_agent
    
    # Получаем инструменты из реестра
    tools = get_all_tools()
    logger.info(f"Initializing agent with {len(tools)} tools")
    
    # Создаем экземпляр агента с инструментами из реестра
    investment_agent = Agent(
        name="InvestmentAdvisor",
        instructions=INVESTMENT_ADVISOR_PROMPT,
        model=DEFAULT_MODEL,
        model_settings=model_settings,
        tools=tools
    )
    
    logger.info(f"Investment Agent initialized successfully with {len(tools)} tools")
    return investment_agent

def get_agent():
    """
    Возвращает экземпляр агента, инициализируя его при необходимости.
    
    Returns:
        Agent: Инициализированный агент
    """
    global investment_agent
    if investment_agent is None:
        return initialize_agent()
    return investment_agent