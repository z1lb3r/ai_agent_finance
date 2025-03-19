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
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# Импортируем регистратор инструментов
from tools.registry import register_tool

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sec_downloader")

# Конфигурация
from config import SEC_API_KEY, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
API_KEY = SEC_API_KEY  # Ключ API из конфигурационного файла
OUTPUT_DIR = "downloaded_filings"  # Директория для сохранения файлов

# Эндпоинты SEC API
QUERY_API_URL = "https://api.sec-api.io"  # Для поиска отчетов
PDF_API_URL = "https://api.sec-api.io/filing-reader"  # Для конвертации в PDF

# Эта функция не будет декорирована @register_tool
def api_request_with_retry(method, url, headers=None, params=None, json=None, stream=False, timeout=None):
    """
    Make API request with retry logic for rate limiting
    
    Args:
        method: The HTTP method function to use (e.g., requests.get)
        url: The URL to request
        headers: Optional headers dictionary
        params: Optional query parameters
        json: Optional JSON payload
        stream: Whether to stream the response
        timeout: Request timeout in seconds
        
    Returns:
        The response object
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Build kwargs dict with only provided parameters
            kwargs = {}
            if headers is not None:
                kwargs['headers'] = headers
            if params is not None:
                kwargs['params'] = params  
            if json is not None:
                kwargs['json'] = json
            if stream:
                kwargs['stream'] = stream
            if timeout is not None:
                kwargs['timeout'] = timeout
                
            # Make the request
            response = method(url, **kwargs)
            
            # Check if rate limited
            if response.status_code == 429:
                wait_time = RETRY_DELAY * (2 ** retries) + random.uniform(0, 1)
                logger.warning(f"Rate limited. Waiting for {wait_time:.2f} seconds before retry.")
                time.sleep(wait_time)
                retries += 1
                continue
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if retries >= MAX_RETRIES - 1:
                raise
            
            wait_time = RETRY_DELAY * (2 ** retries) + random.uniform(0, 1)
            logger.warning(f"Request failed: {str(e)}. Retrying in {wait_time:.2f} seconds.")
            time.sleep(wait_time)
            retries += 1
            
    raise Exception(f"Failed after {MAX_RETRIES} retries")

@register_tool
def search_filings(ticker: str, form_type: Optional[str] = None, 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, 
                   limit: Optional[int] = None) -> str:
    """
    Поиск отчетов по тикеру с возможностью фильтрации.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-K', '10-Q')
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        limit: Максимальное количество результатов
        
    Returns:
        JSON строка с информацией об отчетах
    """
    # Проверяем API ключ
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        error_msg = "API-ключ SEC API не настроен в конфигурации."
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "ticker": ticker, "count": 0, "filings": []})
    
    # Формируем запрос
    query = f"ticker:{ticker}"
    
    if form_type:
        query += f' AND formType:"{form_type}"'
    
    if start_date and end_date:
        query += f' AND filedAt:[{start_date} TO {end_date}]'
    
    # Обрабатываем limit
    actual_limit = 10
    if limit is not None:
        try:
            actual_limit = int(limit)
        except (ValueError, TypeError):
            actual_limit = 10
    
    # Формируем JSON для запроса
    payload = {
        "query": query,
        "from": "0",
        "size": str(actual_limit),
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    
    # Заголовки запроса
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Поиск отчетов для {ticker}")
        response = api_request_with_retry(
            requests.post, 
            QUERY_API_URL, 
            headers=headers, 
            json=payload, 
            timeout=REQUEST_TIMEOUT
        )
        
        data = response.json()
        
        # Форматируем результаты
        filings = data.get("filings", [])
        
        result = {
            "ticker": ticker,
            "count": len(filings),
            "filings": filings
        }
        
        logger.info(f"Найдено {len(filings)} отчетов для {ticker}")
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Ошибка при поиске отчетов для {ticker}: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "ticker": ticker, "count": 0, "filings": []})

@register_tool
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
        return json.dumps({"error": error_msg})
    
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
        response = api_request_with_retry(
            requests.get,
            PDF_API_URL,
            params=params,
            stream=True,
            timeout=REQUEST_TIMEOUT
        )
        
        # Сохраняем файл
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Документ успешно скачан: {output_path}")
        return json.dumps({"file_path": output_path, "success": True})
    
    except Exception as e:
        error_msg = f"Ошибка при скачивании документа: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "success": False})

@register_tool
def get_recent_filing(ticker: str, form_type: Optional[str] = None) -> str:
    """
    Получить самый последний отчет определенного типа для компании.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-Q')
        
    Returns:
        JSON строка с информацией о найденном отчете или ошибкой
    """
    # Ищем отчеты
    actual_form_type = "10-Q"
    if form_type is not None:
        actual_form_type = form_type
        
    filings_data = json.loads(search_filings(ticker, actual_form_type, limit=1))
    
    # Проверяем наличие ошибок и результатов
    if "error" in filings_data:
        return json.dumps({"error": filings_data["error"], "ticker": ticker})
    
    if filings_data["count"] == 0:
        return json.dumps({"error": f"Отчеты типа {actual_form_type} не найдены для {ticker}", "ticker": ticker})
    
    # Возвращаем первый найденный отчет (самый новый)
    return json.dumps({
        "ticker": ticker,
        "filing": filings_data["filings"][0]
    })

@register_tool
def download_recent_filing_as_pdf(ticker: str, form_type: Optional[str] = None) -> str:
    """
    Скачать самый последний отчет определенного типа для компании в формате PDF.
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-Q')
        
    Returns:
        Путь к скачанному файлу или сообщение об ошибке
    """
    # Установка формы отчета по умолчанию, если не указана
    actual_form_type = "10-Q"
    if form_type is not None:
        actual_form_type = form_type
        
    # Получаем информацию о последнем отчете
    filing_info = json.loads(get_recent_filing(ticker, actual_form_type))
    
    # Проверяем наличие ошибок
    if "error" in filing_info:
        return json.dumps({"error": filing_info["error"]})
    
    # Получаем URL отчета
    filing = filing_info["filing"]
    filing_url = filing.get("linkToFilingDetails")
    
    if not filing_url:
        return json.dumps({"error": f"URL отчета не найден для {ticker} (тип: {actual_form_type})"})
    
    # Формируем имя файла
    form_type_for_filename = filing.get("formType", actual_form_type)
    filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "unknown_date"
    output_filename = f"{ticker}_{form_type_for_filename}_{filed_date}.pdf"
    
    # Скачиваем PDF
    result = json.loads(download_filing_as_pdf(filing_url, output_filename))
    
    if "error" in result:
        return json.dumps({"error": result["error"]})
    
    return json.dumps({
        "result": f"Downloaded {actual_form_type} report for {ticker}",
        "file_path": result["file_path"]
    })

@register_tool
def search_filings_by_period(ticker: str, form_type: Optional[str] = None, 
                            year: Optional[int] = None, 
                            quarter: Optional[int] = None, 
                            limit: Optional[int] = None) -> str:
    """
    Поиск отчетов по тикеру за указанный период (год/квартал).
    
    Args:
        ticker: Тикер акции (например, 'AAPL')
        form_type: Тип отчета (например, '10-K', '10-Q')
        year: Год (например, 2023)
        quarter: Квартал (1-4)
        limit: Максимальное количество результатов
        
    Returns:
        JSON строка с информацией об отчетах
    """
    # Определяем даты на основе года и квартала
    start_date = None
    end_date = None
    
    if year is not None:
        try:
            year = int(year)
            if quarter is not None:
                quarter = int(quarter)
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
        except (ValueError, TypeError):
            return json.dumps({"error": "Invalid year or quarter value"})
    
    # Выполняем поиск
    return search_filings(ticker, form_type, start_date, end_date, limit)

@register_tool
def format_filing_summary(filing: str) -> str:
    """
    Форматирует отчет для отображения пользователю.
    
    Args:
        filing: JSON строка с данными отчета
        
    Returns:
        Отформатированная строка
    """
    try:
        if isinstance(filing, str):
            filing_data = json.loads(filing)
        else:
            filing_data = filing
    except json.JSONDecodeError:
        return "Ошибка: некорректный формат данных отчета"
    
    form_type = filing_data.get("formType", "Неизвестный тип")
    filed_date = filing_data.get("filedAt", "")[:10] if filing_data.get("filedAt") else "Неизвестная дата"
    description = filing_data.get("description", "Нет описания")
    company = filing_data.get("companyName", "")
    
    # Форматируем период отчета, если доступен
    period = ""
    if filing_data.get("periodOfReport"):
        period = f" за период до {filing_data.get('periodOfReport')}"
    
    return f"{form_type} от {filed_date}{period}: {description}"

@register_tool
def get_filing_list_summary(filings_data: str) -> str:
    """
    Создает текстовое описание списка отчетов.
    
    Args:
        filings_data: JSON строка с результатом функции search_filings
        
    Returns:
        Строка с описанием найденных отчетов
    """
    try:
        if isinstance(filings_data, str):
            data = json.loads(filings_data)
        else:
            data = filings_data
    except json.JSONDecodeError:
        return "Ошибка: некорректный формат данных о отчетах"
    
    if "error" in data:
        return f"Ошибка: {data['error']}"
    
    ticker = data.get("ticker", "Неизвестный тикер")
    count = data.get("count", 0)
    
    if count == 0:
        return f"Для компании {ticker} не найдено отчетов с указанными параметрами."
    
    result = f"Найдено {count} отчетов для {ticker}:\n\n"
    
    for i, filing in enumerate(data.get("filings", []), 1):
        filing_summary = format_filing_summary(filing)
        result += f"{i}. {filing_summary}\n"
    
    return result

@register_tool
def get_company_quarterly_report(ticker: str, year: Optional[int] = None, quarter: Optional[int] = None) -> str:
    """
    Get the most recent quarterly report (10-Q) for a company or for a specific year and quarter.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        year: The specific year to search for
        quarter: The specific quarter (1-4) to search for (requires year to be specified)
        
    Returns:
        JSON строка с информацией о скачанном отчете
    """
    try:
        if year is not None:
            try:
                year = int(year)
                if quarter is not None:
                    quarter = int(quarter)
            except (ValueError, TypeError):
                return json.dumps({"error": "Invalid year or quarter value"})
                
            # Ищем отчет за конкретный год и квартал
            result_json = search_filings_by_period(
                ticker, "10-Q", year, quarter, limit=1
            )
            result = json.loads(result_json)
            
            if result.get("count", 0) == 0:
                period_desc = f"Q{quarter} {year}" if quarter is not None else f"{year}"
                return json.dumps({"error": f"No 10-Q report found for {ticker} for {period_desc}"})
            
            # Берем первый найденный отчет
            filing = result.get("filings", [])[0]
            filing_url = filing.get("linkToFilingDetails")
            
            if not filing_url:
                return json.dumps({"error": "Filing URL not found in the response"})
            
            # Формируем имя файла
            filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "unknown_date"
            output_filename = f"{ticker}_10-Q_{filed_date}.pdf"
            
            # Скачиваем PDF
            download_result = json.loads(download_filing_as_pdf(filing_url, output_filename))
            
            if "error" in download_result:
                return json.dumps({"error": download_result["error"]})
            
            return json.dumps({
                "result": f"Downloaded 10-Q report for {ticker}",
                "filing_date": filed_date,
                "file_path": download_result["file_path"]
            })
        else:
            # Если год не указан, скачиваем самый свежий квартальный отчет
            result = json.loads(download_recent_filing_as_pdf(ticker, "10-Q"))
            
            if "error" in result:
                return json.dumps({"error": result["error"]})
            
            return json.dumps({
                "result": f"Downloaded latest 10-Q report for {ticker}",
                "file_path": result["file_path"]
            })
    except Exception as e:
        logger.error(f"Error in get_company_quarterly_report: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def get_company_annual_report(ticker: str, year: Optional[int] = None) -> str:
    """
    Get the most recent annual report (10-K) for a company or for a specific year.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        year: The specific year to search for
        
    Returns:
        JSON строка с информацией о скачанном отчете
    """
    try:
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                return json.dumps({"error": "Invalid year value"})
                
            # Ищем отчет за конкретный год
            result_json = search_filings_by_period(
                ticker, "10-K", year, None, limit=1
            )
            result = json.loads(result_json)
            
            if result.get("count", 0) == 0:
                return json.dumps({"error": f"No 10-K report found for {ticker} for {year}"})
            
            # Берем первый найденный отчет
            filing = result.get("filings", [])[0]
            filing_url = filing.get("linkToFilingDetails")
            
            if not filing_url:
                return json.dumps({"error": "Filing URL not found in the response"})
            
            # Формируем имя файла
            filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "unknown_date"
            output_filename = f"{ticker}_10-K_{filed_date}.pdf"
            
            # Скачиваем PDF
            download_result = json.loads(download_filing_as_pdf(filing_url, output_filename))
            
            if "error" in download_result:
                return json.dumps({"error": download_result["error"]})
            
            return json.dumps({
                "result": f"Downloaded 10-K report for {ticker} for {year}",
                "filing_date": filed_date,
                "file_path": download_result["file_path"]
            })
        else:
            # Если год не указан, скачиваем самый свежий годовой отчет
            result = json.loads(download_recent_filing_as_pdf(ticker, "10-K"))
            
            if "error" in result:
                return json.dumps({"error": result["error"]})
            
            return json.dumps({
                "result": f"Downloaded latest 10-K report for {ticker}",
                "file_path": result["file_path"]
            })
    except Exception as e:
        logger.error(f"Error in get_company_annual_report: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def get_company_recent_filings(ticker: str, form_type: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Get a list of recent SEC filings for a company.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        form_type: The type of filing to retrieve (e.g., '10-K', '10-Q', '8-K')
        limit: Maximum number of filings to retrieve
        
    Returns:
        JSON строка с информацией о недавних отчетах
    """
    try:
        # Если limit не указан, используем значение по умолчанию
        actual_limit = 5
        if limit is not None:
            try:
                actual_limit = int(limit)
            except (ValueError, TypeError):
                actual_limit = 5
                
        result = json.loads(search_filings(ticker, form_type, limit=actual_limit))
        summary = get_filing_list_summary(result)
        return json.dumps({"result": summary, "filings_count": result.get("count", 0)})
    except Exception as e:
        logger.error(f"Error in get_company_recent_filings: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def download_specific_filing(ticker: str, form_type: str, filing_index: Optional[int] = None) -> str:
    """
    Download a specific filing from search results.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL')
        form_type: The type of filing to retrieve (e.g., '10-K', '10-Q', '8-K')
        filing_index: Index of the filing in search results (0 = most recent)
        
    Returns:
        JSON строка с информацией о скачанном отчете
    """
    try:
        # Если индекс не указан, используем значение по умолчанию
        actual_index = 0
        if filing_index is not None:
            try:
                actual_index = int(filing_index)
            except (ValueError, TypeError):
                actual_index = 0
        
        # Ищем отчеты
        result = json.loads(search_filings(ticker, form_type, limit=actual_index + 1))
        
        if result.get("count", 0) <= actual_index:
            return json.dumps({
                "error": f"No {form_type} filing found for {ticker} at index {actual_index}"
            })
        
        # Получаем нужный отчет по индексу
        filing = result.get("filings", [])[actual_index]
        filing_url = filing.get("linkToFilingDetails")
        
        if not filing_url:
            return json.dumps({"error": "Filing URL not found in the response"})
        
        # Формируем имя файла
        filed_date = filing.get("filedAt", "")[:10] if filing.get("filedAt") else "unknown_date"
        output_filename = f"{ticker}_{form_type}_{filed_date}.pdf"
        
        # Скачиваем PDF
        download_result = json.loads(download_filing_as_pdf(filing_url, output_filename))
        
        if "error" in download_result:
            return json.dumps({"error": download_result["error"]})
        
        return json.dumps({
            "result": f"Downloaded {form_type} report for {ticker}",
            "filing_date": filed_date,
            "file_path": download_result["file_path"],
            "filing_description": format_filing_summary(filing)
        })
        
    except Exception as e:
        logger.error(f"Error in download_specific_filing: {str(e)}")
        return json.dumps({"error": str(e)})