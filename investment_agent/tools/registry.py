"""
Реестр инструментов для инвестиционного агента.
"""

import inspect
import functools
import logging
from typing import List, Callable, Any, Dict, Optional, Union

from agents import function_tool

# Настраиваем логгер
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("investment_agent.tools_registry")

# Глобальный реестр инструментов
TOOL_REGISTRY = []

# Список функций, которые не должны регистрироваться как инструменты
EXCLUDED_FUNCTIONS = [
    "register_tool",
    "get_all_tools",
    "discover_tools_from_module",
    "api_request_with_retry",
    "extract_numerical_data_enhanced",
    "analyze_section_content"
]

def register_tool(func: Callable) -> Callable:
    """
    Декоратор для регистрации функции как инструмента в реестре.
    
    Args:
        func: Функция для регистрации
        
    Returns:
        Оригинальная функция (не обернутая в function_tool)
    """
    # Проверяем, не в списке ли исключений эта функция
    if func.__name__ in EXCLUDED_FUNCTIONS:
        logger.info(f"Пропуск регистрации функции {func.__name__} - она в списке исключений")
        return func
    
    # Проверяем, не зарегистрирована ли функция уже
    if any(getattr(tool, 'name', None) == func.__name__ for tool in TOOL_REGISTRY):
        logger.info(f"Инструмент {func.__name__} уже зарегистрирован, пропускаем")
        return func
    
    try:
        # Создаем инструмент с помощью SDK
        tool_func = function_tool(func)
        
        # Регистрируем в глобальном реестре
        TOOL_REGISTRY.append(tool_func)
        logger.info(f"Инструмент зарегистрирован: {func.__name__}")
        
        # Возвращаем оригинальную функцию для использования в коде
        return func
            
    except Exception as e:
        logger.error(f"Ошибка при регистрации инструмента {func.__name__}: {str(e)}")
        # Возвращаем оригинальную функцию без преобразования в инструмент
        return func

def get_all_tools() -> List:
    """
    Возвращает все зарегистрированные инструменты.
    
    Returns:
        Список всех зарегистрированных инструментов
    """
    return TOOL_REGISTRY

def get_tool_info() -> List[Dict]:
    """
    Возвращает информацию о всех инструментах в удобочитаемом формате.
    
    Returns:
        Список словарей с информацией об инструментах
    """
    tools_info = []
    
    for tool in TOOL_REGISTRY:
        tool_info = {
            "name": getattr(tool, 'name', str(tool)),
            "description": getattr(tool, 'description', ""),
            "parameters": getattr(tool, 'parameters', {}) if hasattr(tool, 'parameters') else {}
        }
        tools_info.append(tool_info)
    
    return tools_info

def discover_tools_from_module(module: Any) -> None:
    """
    Обнаруживает и регистрирует функции-инструменты из указанного модуля.
    Используется только при первичной инициализации.
    
    Args:
        module: Модуль Python для сканирования
    """
    for name, item in inspect.getmembers(module, inspect.isfunction):
        # Пропускаем функции из списка исключений
        if name in EXCLUDED_FUNCTIONS:
            continue
            
        # Пропускаем функции, которые уже зарегистрированы
        if any(getattr(tool, 'name', None) == name for tool in TOOL_REGISTRY):
            continue
            
        # Проверяем, что функция имеет документацию и аннотации типов
        if inspect.getdoc(item) and hasattr(item, "__annotations__"):
            try:
                # Регистрируем функцию как инструмент
                register_tool(item)
                logger.info(f"Инструмент обнаружен и зарегистрирован из модуля: {name}")
            except Exception as e:
                logger.error(f"Ошибка при обработке функции {name}: {str(e)}")

def get_tools_by_category(category: str) -> List:
    """
    Возвращает инструменты по категории (предполагается, что категория указана в метаданных).
    
    Args:
        category: Категория для фильтрации инструментов
        
    Returns:
        Список инструментов в указанной категории
    """
    return [tool for tool in TOOL_REGISTRY if getattr(tool, "category", None) == category]