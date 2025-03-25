#!/usr/bin/env python
"""
Скрипт для запуска инвестиционного агента с одним запросом.
Возвращает ответ агента в стандартный вывод.

Использование:
    python run_agent.py "Ваш запрос к инвестиционному агенту"
"""

import os
import sys
import json
import logging
import traceback
import importlib
from typing import List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='run_agent.log'  # Для отладки
)
logger = logging.getLogger("run_agent")

def discover_and_import_all_tools() -> List[str]:
    """
    Автоматически обнаруживает и импортирует все модули с инструментами.
    
    Returns:
        Список имен успешно импортированных модулей
    """
    imported_modules = []
    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools')
    
    logger.info(f"Сканирование директории с инструментами: {tools_dir}")
    
    # Получаем список всех Python-файлов в директории tools
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"tools.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
                imported_modules.append(module_name)
                logger.info(f"Импортирован модуль: {module_name}")
            except ImportError as e:
                logger.error(f"Ошибка импорта модуля {module_name}: {str(e)}")
    
    return imported_modules

def main():
    """
    Основная функция скрипта.
    """
    try:
        # Проверяем наличие запроса
        if len(sys.argv) < 2:
            error_msg = "Запрос не предоставлен"
            logger.error(error_msg)
            print(json.dumps({"success": False, "error": error_msg}))
            sys.exit(1)
        
        # Получаем запрос
        query = sys.argv[1]
        logger.info(f"Получен запрос: {query}")
        
        # Импортируем все модули с инструментами
        imported_modules = discover_and_import_all_tools()
        logger.info(f"Импортировано модулей с инструментами: {len(imported_modules)}")
        
        # Импортируем компоненты для запуска агента
        # Важно делать это после импорта всех инструментов
        from agent import get_agent
        from agents import Runner, RunConfig
        
        # Инициализируем агента
        logger.info("Инициализация инвестиционного агента")
        investment_agent = get_agent()
        
        # Создаем конфигурацию для запуска
        run_config = RunConfig(
            tracing_disabled=True,
            workflow_name="Investment Query"
        )
        
        # Обрабатываем запрос
        logger.info("Обработка запроса инвестиционным агентом")
        response = Runner.run_sync(investment_agent, query, run_config=run_config)
        
        # Получаем ответ от агента
        final_output = response.final_output
        logger.info(f"Получен ответ от агента (первые 200 символов): {final_output[:200] if final_output else 'пустой ответ'}")
        
        # Проверяем, не пустой ли ответ
        if not final_output or final_output.isspace():
            logger.warning("Агент вернул пустой ответ")
            final_output = "Извините, не удалось получить информацию по вашему запросу."
        
        # Выводим результат в стандартный вывод
        result = {
            "success": True,
            "response": final_output
        }
        
        # Используем ensure_ascii=False для корректной обработки кириллицы
        json_result = json.dumps(result, ensure_ascii=False)
        print(json_result)
        logger.info("Запрос успешно обработан")
        
    except Exception as e:
        error_msg = f"Ошибка при обработке запроса: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        print(json.dumps({
            "success": False,
            "error": error_msg,
            "traceback": traceback.format_exc()
        }, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()