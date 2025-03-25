#!/usr/bin/env python
"""
CLI-интерфейс для инвестиционного агента.

Этот скрипт обрабатывает запросы от мастер-агента через командную строку,
возвращая ответы в stdout в формате JSON.

Использование:
    python cli_agent.py "Ваш запрос к инвестиционному агенту"
    
    или через stdin:
    echo "Ваш запрос" | python cli_agent.py
"""

import sys
import json
import traceback
import logging
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='cli_agent.log'  # Запись логов в файл для отладки
)
logger = logging.getLogger("cli_agent")

def process_query(query: str) -> Dict[str, Any]:
    """
    Обрабатывает запрос к инвестиционному агенту.
    
    Args:
        query: Текст запроса
        
    Returns:
        Словарь с ответом или сообщением об ошибке
    """
    try:
        # Импортируем нужные компоненты инвестиционного агента
        from agent import get_agent
        from agents import Runner, RunConfig
        
        # Получаем экземпляр агента
        investment_agent = get_agent()
        
        # Создаем конфигурацию для запуска
        run_config = RunConfig(
            tracing_disabled=True,
            workflow_name="Investment CLI Query"
        )
        
        # Обрабатываем запрос
        response = Runner.run_sync(investment_agent, query, run_config=run_config)
        
        # Возвращаем результат
        return {
            "success": True,
            "response": response.final_output
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "message": "Произошла ошибка при обработке запроса инвестиционным агентом."
        }

def main():
    """
    Основная функция CLI-интерфейса.
    """
    try:
        # Проверяем, получен ли запрос как аргумент командной строки
        if len(sys.argv) > 1:
            query = sys.argv[1]
        # Если нет, пробуем прочитать из stdin
        elif not sys.stdin.isatty():
            query = sys.stdin.read().strip()
        else:
            print(json.dumps({
                "success": False,
                "error": "No query provided",
                "message": "Запрос не предоставлен. Используйте аргумент командной строки или stdin."
            }))
            sys.exit(1)
        
        # Обрабатываем запрос
        logger.info(f"Processing query: {query}")
        result = process_query(query)
        
        # Выводим результат в stdout в формате JSON
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"CLI error: {str(e)}")
        logger.error(traceback.format_exc())
        
        print(json.dumps({
            "success": False,
            "error": str(e),
            "message": "Произошла ошибка в CLI-интерфейсе инвестиционного агента."
        }, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()