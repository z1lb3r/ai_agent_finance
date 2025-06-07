"""
RAG Analyzer - Инструмент для анализа с использованием Retrieval-Augmented Generation.

Этот модуль предоставляет функции для извлечения контекстуальной информации 
из документов для расширенного анализа различных секторов рынка.
"""

import os
import logging
import json
from docx import Document
from typing import Dict, List, Optional, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rag_analyzer")

# Путь к папке с данными
DATASETS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets")

def extract_text_from_docx(file_path: str) -> str:
    """
    Извлекает текст из документа Word.
    
    Args:
        file_path: Путь к документу Word
        
    Returns:
        Извлеченный текст
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return f"Error: Файл не найден: {file_path}"
        
        doc = Document(file_path)
        full_text = []
        
        for para in doc.paragraphs:
            full_text.append(para.text)
            
        return "\n".join(full_text)
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из документа: {str(e)}")
        return f"Error: Ошибка при извлечении текста из документа: {str(e)}"

def get_bank_stock_analysis_context() -> Dict[str, Any]:
    """
    Получает контекст для анализа банковских акций из RAG-документа.
    
    Returns:
        Словарь с извлеченным контекстом
    """
    try:
        # Путь к документу banksRAG.docx
        rag_file_path = os.path.join(DATASETS_PATH, "banksRAG.docx")
        
        # Проверка наличия файла
        if not os.path.exists(rag_file_path):
            logger.error(f"RAG-документ не найден: {rag_file_path}")
            return {"error": f"RAG-документ не найден: {rag_file_path}"}
        
        # Извлечение текста из документа
        rag_text = extract_text_from_docx(rag_file_path)
        
        if rag_text.startswith("Error:"):
            return {"error": rag_text}
        
        # Возвращаем контекст для анализа
        return {
            "context_type": "bank_stock_analysis",
            "context_text": rag_text,
            "source": "banksRAG.docx"
        }
    except Exception as e:
        logger.error(f"Ошибка при получении контекста для анализа банковских акций: {str(e)}")
        return {"error": str(e)}

def is_bank_stock_query(query: str) -> bool:
    """
    Определяет, относится ли запрос к банковским акциям.
    
    Args:
        query: Текст запроса пользователя
        
    Returns:
        True, если запрос относится к банковским акциям, иначе False
    """
    query_lower = query.lower()
    return "bank stock" in query_lower or "банковского сектора" in query_lower