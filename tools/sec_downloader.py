"""
SEC Downloader - Модуль для скачивания отчетов SEC в формате PDF

Этот модуль предоставляет функциональность для:
1. Поиска отчетов компании по тикеру
2. Скачивания найденных отчетов в формате PDF

Интегрирован с OpenAI Agents SDK для использования в качестве инструментов агента.
"""

import requests
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sec_downloader")

# Конфигурация
from config import SEC_API_KEY, REQUEST_TIMEOUT
API_KEY = SEC_API_KEY  # Ключ API из конфигурационного файла
OUTPUT_DIR = "downloaded_filings"  # Директория для сохранения файлов

# Эндпоинты SEC API
QUERY_API_URL = "https://api.sec-api.io"  # Для поиска отчетов
PDF_API_URL = "https://api.sec-api.io/filing-reader"  # Для конвертации в PDF

def search_filings(ticker: str, form_type: Optional[str] = None, 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, 
                   limit: int = 10) -> Dict:
    """
    Поиск отчетов по тикеру с возможностью фильтрации.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-K', '10-Q')
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        limit: Максимальное количество результатов
        
    Returns:
        Словарь с информацией об отчетах
    """
    # Проверяем API ключ
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        error_msg = "API-ключ SEC API не настроен в конфигурации."
        logger.error(error_msg)
        return {"error": error_msg, "ticker": ticker, "count": 0, "filings": []}
    
    # Формируем запрос
    query = f"ticker:{ticker}"
    
    if form_type:
        query += f' AND formType:"{form_type}"'
    
    if start_date and end_date:
        query += f' AND filedAt:[{start_date} TO {end_date}]'
    
    # Формируем JSON для запроса
    payload = {
        "query": query,
        "from": "0",
        "size": str(limit),
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    
    # Заголовки запроса
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Поиск отчетов для {ticker}")
        response = requests.post(QUERY_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Форматируем результаты
        filings = data.get("filings", [])
        
        result = {
            "ticker": ticker,
            "count": len(filings),
            "filings": filings
        }
        
        logger.info(f"Найдено {len(filings)} отчетов для {ticker}")
        return result
        
    except Exception as e:
        error_msg = f"Ошибка при поиске отчетов для {ticker}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "ticker": ticker, "count": 0, "filings": []}

def download_filing_as_pdf(filing_url: str, output_filename: Optional[str] = None) -> str:
    """
    Скачать отчет как PDF с использованием PDF Generator API.
    
    Args:
        filing_url: URL файла отчета (из поля linkToFilingDetails в Query API)
        output_filename: Имя файла для сохранения (если не указано, генерируется автоматически)
        
    Returns:
        Путь к скачанному файлу или сообщение об ошибке
    """
    # Проверяем API ключ
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        error_msg = "API-ключ SEC API не настроен в конфигурации."
        logger.error(error_msg)
        return error_msg
    
    try:
        # Создаем директорию, если она не существует
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Если имя файла не указано, генерируем его из URL
        if not output_filename:
            # Извлекаем имя файла из URL
            filename_base = os.path.basename(filing_url).split('.')[0]
            output_filename = f"{filename_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Формируем URL для API
        params = {
            "token": API_KEY,
            "url": filing_url
        }
        
        logger.info(f"Скачивание документа в PDF: {output_filename}")
        
        # Делаем запрос
        response = requests.get(PDF_API_URL, params=params, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Сохраняем файл
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Документ успешно скачан: {output_path}")
        return output_path
    
    except Exception as e:
        error_msg = f"Ошибка при скачивании документа: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_recent_filing(ticker: str, form_type: str = "10-Q") -> Dict:
    """
    Получить самый последний отчет определенного типа для компании.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (по умолчанию '10-Q')
        
    Returns:
        Словарь с информацией о найденном отчете или ошибкой
    """
    # Ищем отчеты
    filings_data = search_filings(ticker, form_type, limit=1)
    
    # Проверяем наличие ошибок и результатов
    if "error" in filings_data:
        return {"error": filings_data["error"], "ticker": ticker}
    
    if filings_data["count"] == 0:
        return {"error": f"Отчеты типа {form_type} не найдены для {ticker}", "ticker": ticker}
    
    # Возвращаем первый найденный отчет (самый новый)
    return {
        "ticker": ticker,
        "filing": filings_data["filings"][0]
    }

def download_recent_filing_as_pdf(ticker: str, form_type: str = "10-Q") -> str:
    """
    Скачать самый последний отчет определенного типа для компании в формате PDF.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (по умолчанию '10-Q')
        
    Returns:
        Путь к скачанному файлу или сообщение об ошибке
    """
    # Получаем информацию о последнем отчете
    filing_info = get_recent_filing(ticker, form_type)
    
    # Проверяем наличие ошибок
    if "error" in filing_info:
        return filing_info["error"]
    
    # Получаем URL отчета
    filing = filing_info["filing"]
    filing_url = filing.get("linkToFilingDetails")
    
    if not filing_url:
        return f"URL отчета не найден для {ticker} (тип: {form_type})"
    
    # Формируем имя файла
    form_type = filing.get("formType", form_type)
    filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "unknown_date"
    output_filename = f"{ticker}_{form_type}_{filed_date}.pdf"
    
    # Скачиваем PDF
    return download_filing_as_pdf(filing_url, output_filename)

def search_filings_by_period(ticker: str, form_type: Optional[str] = None, 
                            year: Optional[int] = None, 
                            quarter: Optional[int] = None, 
                            limit: int = 10) -> Dict:
    """
    Поиск отчетов по тикеру за указанный период (год/квартал).
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-K', '10-Q')
        year: Год (например, 2023)
        quarter: Квартал (1-4)
        limit: Максимальное количество результатов
        
    Returns:
        Словарь с информацией об отчетах
    """
    # Определяем даты на основе года и квартала
    start_date = None
    end_date = None
    
    if year:
        if quarter:
            # Определяем диапазон дат для указанного квартала
            if quarter == 1:
                start_date = f"{year}-01-01"
                end_date = f"{year}-03-31"
            elif quarter == 2:
                start_date = f"{year}-04-01"
                end_date = f"{year}-06-30"
            elif quarter == 3:
                start_date = f"{year}-07-01"
                end_date = f"{year}-09-30"
            elif quarter == 4:
                start_date = f"{year}-10-01"
                end_date = f"{year}-12-31"
        else:
            # Весь год
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
    
    # Выполняем поиск
    return search_filings(ticker, form_type, start_date, end_date, limit)

def format_filing_summary(filing: Dict) -> str:
    """
    Форматирует отчет для отображения пользователю.
    
    Args:
        filing: Словарь с данными отчета
        
    Returns:
        Отформатированная строка
    """
    form_type = filing.get("formType", "Неизвестный тип")
    filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "Неизвестная дата"
    description = filing.get("description", "Нет описания")
    company = filing.get("companyName", "")
    
    # Форматируем период отчета, если доступен
    period = ""
    if filing.get("periodOfReport"):
        period = f" за период до {filing.get('periodOfReport')}"
    
    return f"{form_type} от {filed_date}{period}: {description}"

def get_filing_list_summary(filings_data: Dict) -> str:
    """
    Создает текстовое описание списка отчетов.
    
    Args:
        filings_data: Результат функции search_filings
        
    Returns:
        Строка с описанием найденных отчетов
    """
    if "error" in filings_data:
        return f"Ошибка: {filings_data['error']}"
    
    ticker = filings_data.get("ticker", "Неизвестный тикер")
    count = filings_data.get("count", 0)
    
    if count == 0:
        return f"Для компании {ticker} не найдено отчетов с указанными параметрами."
    
    result = f"Найдено {count} отчетов для {ticker}:\n\n"
    
    for i, filing in enumerate(filings_data.get("filings", []), 1):
        result += f"{i}. {format_filing_summary(filing)}\n"
    
    return result