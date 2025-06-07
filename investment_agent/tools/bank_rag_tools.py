"""
Bank RAG Tools - Инструменты для анализа акций банковского сектора с использованием RAG.

Этот модуль предоставляет инструменты для расширенного анализа акций банковского 
сектора с использованием контекстуальной информации из RAG-документов.
"""

import json
import logging
from typing import Dict, Any, Optional

from tools.registry import register_tool
from tools.rag_analyzer import get_bank_stock_analysis_context, is_bank_stock_query

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bank_rag_tools")

@register_tool
def provide_bank_analysis_context(user_query: str) -> str:
    """
    Предоставляет контекстуальную информацию для анализа банковских акций, если запрос касается банковского сектора.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        JSON-строка с контекстуальной информацией или сообщением об ошибке
    """
    try:
        # ДОБАВИТЬ ЭТИ СТРОКИ ЛОГИРОВАНИЯ ЗДЕСЬ
        logger.info(f"Проверка банковского запроса: {user_query}")
        
        # Проверяем, относится ли запрос к банковским акциям
        result = is_bank_stock_query(user_query)
        
        # ДОБАВИТЬ ЭТУ СТРОКУ ЛОГИРОВАНИЯ ЗДЕСЬ
        logger.info(f"Результат проверки: {result}")
        
        if not result:
            # ДОБАВИТЬ ЭТУ СТРОКУ ЛОГИРОВАНИЯ ЗДЕСЬ
            logger.info("Запрос не относится к банковскому сектору, выход из функции")
            return json.dumps({
                "is_bank_query": False,
                "message": "Запрос не относится к банковскому сектору."
            })
        
        # Получаем контекст для анализа банковских акций
        # ДОБАВИТЬ ЭТУ СТРОКУ ЛОГИРОВАНИЯ ЗДЕСЬ
        logger.info("Получение контекста для анализа банковских акций")
        context = get_bank_stock_analysis_context()
        
        # ДОБАВИТЬ ЭТУ СТРОКУ ЛОГИРОВАНИЯ ЗДЕСЬ
        logger.info(f"Получен контекст: {'успешно' if 'error' not in context else context['error']}")
        
        if "error" in context:
            return json.dumps({
                "is_bank_query": True,
                "error": context["error"]
            })
        
        # Возвращаем контекст
        # ДОБАВИТЬ ЭТУ СТРОКУ ЛОГИРОВАНИЯ ЗДЕСЬ
        logger.info(f"Отправка контекста размером {len(context.get('context_text', ''))} символов")
        
        return json.dumps({
            "is_bank_query": True,
            "context": context
        })
    except Exception as e:
        logger.error(f"Ошибка при предоставлении контекста для анализа банковских акций: {str(e)}")
        return json.dumps({
            "is_bank_query": True,
            "error": str(e)
        })