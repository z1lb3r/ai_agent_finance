"""
Инвестиционный агент, предоставляющий функциональность для анализа инвестиций,
работы с SEC EDGAR API и управления портфелем.
"""

import os
import importlib
import logging
from typing import Dict, Any, Optional

# Настраиваем логгер
logger = logging.getLogger(__name__)

# Версия пакета
__version__ = "0.1.0"

# Глобальные переменные агента
_agent_instance = None
_tools_initialized = False

def get_agent():
    """
    Возвращает экземпляр агента, инициализируя его при необходимости.
    
    Returns:
        Agent: Инициализированный агент
    """
    global _agent_instance
    
    if _agent_instance is None:
        # Импортируем здесь для избежания циклических импортов
        from investment_agent.agent import initialize_agent
        _agent_instance = initialize_agent()
        
    return _agent_instance

def initialize_tools():
    """
    Инициализирует все инструменты агента.
    
    Returns:
        bool: True если инициализация прошла успешно, иначе False
    """
    global _tools_initialized
    
    if _tools_initialized:
        return True
    
    try:
        # Импортируем реестр инструментов
        from investment_agent.tools.registry import discover_tools_from_module
        
        # Инициализируем все модули с инструментами
        tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
        modules_initialized = []
        
        # Проверяем наличие директории
        if not os.path.exists(tools_dir):
            logger.warning(f"Директория инструментов не найдена: {tools_dir}")
            return False
        
        # Импортируем все модули с инструментами
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = f"investment_agent.tools.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    modules_initialized.append(module_name)
                    # Обнаруживаем инструменты в импортированном модуле
                    discover_tools_from_module(module)
                    logger.debug(f"Импортирован модуль с инструментами: {module_name}")
                except ImportError as e:
                    logger.error(f"Не удалось импортировать модуль {module_name}: {str(e)}")
        
        logger.info(f"Инициализировано {len(modules_initialized)} модулей с инструментами")
        _tools_initialized = True
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации инструментов: {str(e)}")
        return False

def query(query_text: str) -> Dict[str, Any]:
    """
    Обрабатывает запрос к инвестиционному агенту.
    
    Args:
        query_text: Текст запроса
    
    Returns:
        Dict: Результат обработки запроса 
    """
    try:
        # Инициализируем инструменты, если не инициализированы
        if not _tools_initialized:
            initialize_tools()
        
        # Получаем экземпляр агента
        agent = get_agent()
        
        # Импортируем необходимые компоненты
        from agents import Runner, RunConfig
        
        # Создаем конфигурацию для запуска
        run_config = RunConfig(
            tracing_disabled=True,
            workflow_name="Investment Query"
        )
        
        # Используем другой подход - запускаем в отдельном потоке
        import threading
        import time
        import queue
        import asyncio
        
        result_queue = queue.Queue()
        
        def run_in_thread():
            try:
                # Создаем новый event loop для этого потока
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                
                # Выполняем запрос в этом потоке с новым event loop
                response = Runner.run_sync(agent, query_text, run_config=run_config)
                result_queue.put({"success": True, "response": response.final_output})
                
                # Закрываем loop
                new_loop.close()
            except Exception as e:
                result_queue.put({"success": False, "error": str(e), "response": f"Ошибка в потоке: {str(e)}"})
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True  # Делаем поток демоном, чтобы он завершился при завершении основного потока
        thread.start()
        
        # Ждем результат с таймаутом
        timeout = 60  # 60 секунд таймаут
        try:
            result = result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            # Превышен таймаут ожидания
            return {
                "success": False,
                "error": f"Превышен таймаут ожидания ({timeout} секунд)",
                "response": f"Запрос не был обработан за {timeout} секунд. Попробуйте упростить запрос или повторить позже."
            }

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "response": f"Произошла ошибка при обработке запроса: {str(e)}"
        }