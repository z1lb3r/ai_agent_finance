"""
Bybit API Tool - Инструмент для получения криптовалютных котировок с биржи Bybit

Этот модуль предоставляет функциональность для:
1. Получения текущих котировок по символу
2. Получения исторических данных (свечей) за период
3. Получения списка доступных торговых пар
"""

import requests
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

# Импортируем регистратор инструментов
from .registry import register_tool

# Импортируем конфигурацию
from investment_agent.config import BYBIT_TESTNET, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bybit_api")

# Конфигурация Bybit API
BYBIT_BASE_URL = "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"

# Допустимые интервалы для исторических данных
VALID_INTERVALS = ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"]

# Допустимые категории инструментов
VALID_CATEGORIES = ["spot", "linear", "inverse", "option"]

def _make_api_request(endpoint: str, params: Dict = None) -> Dict:
    """
    Выполняет HTTP запрос к Bybit API с повторными попытками
    
    Args:
        endpoint: API эндпоинт (например, '/v5/market/tickers')
        params: Параметры запроса
        
    Returns:
        Словарь с ответом API
    """
    url = f"{BYBIT_BASE_URL}{endpoint}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # Проверяем успешность ответа Bybit
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg', 'Unknown error')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise Exception(f"Failed to connect to Bybit API after {MAX_RETRIES} attempts: {str(e)}")
            
            logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            time.sleep(RETRY_DELAY * (attempt + 1))
    
    raise Exception("Max retries exceeded")

def _format_symbol(symbol: str) -> str:
    """
    Форматирует символ торговой пары
    
    Args:
        symbol: Символ пары (например, 'btc/usdt', 'BTC-USDT', 'BTCUSDT')
        
    Returns:
        Отформатированный символ в формате BTCUSDT
    """
    # Убираем пробелы и приводим к верхнему регистру
    symbol = symbol.strip().upper()
    
    # Убираем разделители
    symbol = symbol.replace("/", "").replace("-", "").replace("_", "")
    
    return symbol

def _validate_category(category: str) -> str:
    """
    Валидирует категорию инструмента
    
    Args:
        category: Категория инструмента
        
    Returns:
        Валидная категория
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Valid options: {', '.join(VALID_CATEGORIES)}")
    
    return category

def _validate_interval(interval: str) -> str:
    """
    Валидирует интервал для исторических данных
    
    Args:
        interval: Интервал времени
        
    Returns:
        Валидный интервал
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Invalid interval '{interval}'. Valid options: {', '.join(VALID_INTERVALS)}")
    
    return interval

def _calculate_candles_needed(days: int, interval: str) -> int:
    """
    Рассчитывает приблизительное количество свечей для заданного периода и интервала.
    
    Args:
        days: Количество дней
        interval: Интервал времени
        
    Returns:
        Приблизительное количество свечей
    """
    minutes_per_day = 24 * 60
    total_minutes = days * minutes_per_day
    
    if interval == "1":
        return total_minutes
    elif interval == "3":
        return total_minutes // 3
    elif interval == "5":
        return total_minutes // 5
    elif interval == "15":
        return total_minutes // 15
    elif interval == "30":
        return total_minutes // 30
    elif interval == "60":
        return total_minutes // 60
    elif interval == "120":
        return total_minutes // 120
    elif interval == "240":
        return total_minutes // 240
    elif interval == "360":
        return total_minutes // 360
    elif interval == "720":
        return total_minutes // 720
    elif interval == "D":
        return days
    elif interval == "W":
        return days // 7
    elif interval == "M":
        return days // 30
    else:
        return days  # Фоллбэк

@register_tool
def get_crypto_price(symbol: str, category: str = "spot") -> str:
    """
    Получает текущую котировку криптовалютной пары с биржи Bybit.
    
    Args:
        symbol: Символ торговой пары (например, 'BTCUSDT', 'ETHUSDT', 'BTC/USDT')
        category: Категория инструмента ('spot', 'linear', 'inverse', 'option')
        
    Returns:
        JSON строка с данными о котировке
    """
    try:
        # Форматируем и валидируем входные данные
        symbol = _format_symbol(symbol)
        category = _validate_category(category)
        
        # Параметры запроса
        params = {
            "category": category,
            "symbol": symbol
        }
        
        logger.info(f"Получение котировки для {symbol} в категории {category}")
        
        # Выполняем запрос
        data = _make_api_request("/v5/market/tickers", params)
        
        # Извлекаем данные котировки
        ticker_list = data.get("result", {}).get("list", [])
        
        if not ticker_list:
            return json.dumps({
                "error": f"Котировка для символа {symbol} не найдена в категории {category}",
                "symbol": symbol,
                "category": category
            })
        
        ticker = ticker_list[0]  # Берем первый результат
        
        # Форматируем результат
        result = {
            "symbol": ticker.get("symbol"),
            "category": category,
            "last_price": ticker.get("lastPrice"),
            "bid_price": ticker.get("bid1Price"),
            "ask_price": ticker.get("ask1Price"),
            "high_24h": ticker.get("highPrice24h"),
            "low_24h": ticker.get("lowPrice24h"),
            "volume_24h": ticker.get("volume24h"),
            "turnover_24h": ticker.get("turnover24h"),
            "price_change_24h_percent": ticker.get("price24hPcnt"),
            "prev_price_24h": ticker.get("prevPrice24h"),
            "timestamp": datetime.now().isoformat(),
            "exchange": "Bybit"
        }
        
        logger.info(f"Котировка {symbol} получена успешно: {result['last_price']}")
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Ошибка при получении котировки {symbol}: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "symbol": symbol, "category": category})

@register_tool
def get_crypto_history(symbol: str, interval: str, days: int = 7, category: str = "spot", auto_extend: bool = False) -> str:
    """
    Получает исторические данные (свечи) для криптовалютной пары за указанный период.
    
    Args:
        symbol: Символ торговой пары (например, 'BTCUSDT', 'ETHUSDT')
        interval: Интервал времени ('1', '5', '15', '30', '60', '240', 'D', 'W', 'M')
        days: Количество дней назад для получения данных (по умолчанию 7)
        category: Категория инструмента ('spot', 'linear', 'inverse')
        auto_extend: Если True, автоматически делает несколько запросов для получения всех данных
        
    Returns:
        JSON строка с историческими данными
    """
    try:
        # Форматируем и валидируем входные данные
        symbol = _format_symbol(symbol)
        category = _validate_category(category)
        interval = _validate_interval(interval)
        
        # Рассчитываем временные рамки
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Если auto_extend включен, проверяем нужно ли несколько запросов
        estimated_candles = _calculate_candles_needed(days, interval)
        max_per_request = 1000
        
        if auto_extend and estimated_candles > max_per_request:
            # Делаем несколько запросов
            logger.info(f"Требуется ~{estimated_candles} свечей, делаем несколько запросов")
            
            all_klines = []
            requests_needed = min(5, (estimated_candles + max_per_request - 1) // max_per_request)  # Максимум 5 запросов
            
            for i in range(requests_needed):
                # Рассчитываем временной интервал для каждого запроса
                time_per_chunk = timedelta(days=days) / requests_needed
                chunk_end = end_time - (time_per_chunk * i)
                chunk_start = chunk_end - time_per_chunk
                
                chunk_start_ts = int(chunk_start.timestamp() * 1000)
                chunk_end_ts = int(chunk_end.timestamp() * 1000)
                
                # Параметры запроса для этого чанка
                params = {
                    "category": category,
                    "symbol": symbol,
                    "interval": interval,
                    "start": chunk_start_ts,
                    "end": chunk_end_ts,
                    "limit": max_per_request
                }
                
                logger.info(f"Запрос {i+1}/{requests_needed}: {chunk_start.strftime('%Y-%m-%d %H:%M')} - {chunk_end.strftime('%Y-%m-%d %H:%M')}")
                
                # Выполняем запрос
                try:
                    data = _make_api_request("/v5/market/kline", params)
                    klines = data.get("result", {}).get("list", [])
                    all_klines.extend(klines)
                    
                    # Небольшая пауза между запросами
                    if i < requests_needed - 1:
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.warning(f"Ошибка в запросе {i+1}: {str(e)}")
                    continue
            
            # Убираем дубликаты и сортируем
            unique_klines = {}
            for kline in all_klines:
                timestamp = kline[0]
                unique_klines[timestamp] = kline
            
            klines = list(unique_klines.values())
            
        else:
            # Обычный одиночный запрос
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            params = {
                "category": category,
                "symbol": symbol,
                "interval": interval,
                "start": start_timestamp,
                "end": end_timestamp,
                "limit": max_per_request
            }
            
            logger.info(f"Получение исторических данных для {symbol}, интервал {interval}, дней: {days}")
            
            # Выполняем запрос
            data = _make_api_request("/v5/market/kline", params)
            klines = data.get("result", {}).get("list", [])
        
        if not klines:
            return json.dumps({
                "error": f"Исторические данные для {symbol} не найдены",
                "symbol": symbol,
                "interval": interval,
                "category": category
            })
        
        # Преобразуем данные в более читаемый формат
        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                "timestamp": int(kline[0]),
                "datetime": datetime.fromtimestamp(int(kline[0]) / 1000).isoformat(),
                "open_price": kline[1],
                "high_price": kline[2],
                "low_price": kline[3],
                "close_price": kline[4],
                "volume": kline[5],
                "turnover": kline[6]
            })
        
        # Сортируем по времени (от старых к новым)
        formatted_klines.sort(key=lambda x: x["timestamp"])
        
        result = {
            "symbol": symbol,
            "category": category,
            "interval": interval,
            "period_days": days,
            "data_count": len(formatted_klines),
            "klines": formatted_klines,
            "exchange": "Bybit",
            "auto_extend_used": auto_extend and estimated_candles > max_per_request,
            "estimated_candles": estimated_candles if auto_extend else None
        }
        
        logger.info(f"Исторические данные для {symbol} получены: {len(formatted_klines)} свечей")
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Ошибка при получении исторических данных {symbol}: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "symbol": symbol, "interval": interval, "category": category})

@register_tool
def get_crypto_symbols(category: str = "spot", limit: int = 50) -> str:
    """
    Получает список доступных торговых пар на бирже Bybit.
    
    Args:
        category: Категория инструментов ('spot', 'linear', 'inverse', 'option')
        limit: Максимальное количество символов для возврата (по умолчанию 50)
        
    Returns:
        JSON строка со списком доступных торговых пар
    """
    try:
        # Валидируем категорию
        category = _validate_category(category)
        
        # Параметры запроса
        params = {
            "category": category
        }
        
        logger.info(f"Получение списка торговых пар для категории {category}")
        
        # Выполняем запрос
        data = _make_api_request("/v5/market/tickers", params)
        
        # Извлекаем данные
        tickers = data.get("result", {}).get("list", [])
        
        if not tickers:
            return json.dumps({
                "error": f"Торговые пары для категории {category} не найдены",
                "category": category
            })
        
        # Ограничиваем количество результатов
        limited_tickers = tickers[:limit]
        
        # Форматируем список символов
        symbols = []
        for ticker in limited_tickers:
            symbols.append({
                "symbol": ticker.get("symbol"),
                "last_price": ticker.get("lastPrice"),
                "volume_24h": ticker.get("volume24h"),
                "price_change_24h_percent": ticker.get("price24hPcnt")
            })
        
        result = {
            "category": category,
            "total_available": len(tickers),
            "returned_count": len(symbols),
            "symbols": symbols,
            "exchange": "Bybit"
        }
        
        logger.info(f"Список торговых пар получен: {len(symbols)} из {len(tickers)} доступных")
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Ошибка при получении списка торговых пар для {category}: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "category": category})

@register_tool
def get_crypto_market_summary(symbols_list: str, category: str = "spot") -> str:
    """
    Получает сводку по нескольким криптовалютным парам.
    
    Args:
        symbols_list: Список символов через запятую (например, 'BTCUSDT,ETHUSDT,ADAUSDT')
        category: Категория инструментов ('spot', 'linear', 'inverse')
        
    Returns:
        JSON строка со сводкой по указанным парам
    """
    try:
        # Парсим список символов
        symbols = [_format_symbol(s.strip()) for s in symbols_list.split(',') if s.strip()]
        
        if not symbols:
            return json.dumps({"error": "Список символов пуст"})
        
        # Валидируем категорию
        category = _validate_category(category)
        
        logger.info(f"Получение сводки для символов: {', '.join(symbols)}")
        
        # Получаем данные для всех пар категории
        params = {"category": category}
        data = _make_api_request("/v5/market/tickers", params)
        
        all_tickers = data.get("result", {}).get("list", [])
        
        # Фильтруем только нужные символы
        filtered_tickers = []
        found_symbols = []
        
        for ticker in all_tickers:
            if ticker.get("symbol") in symbols:
                filtered_tickers.append({
                    "symbol": ticker.get("symbol"),
                    "last_price": ticker.get("lastPrice"),
                    "price_change_24h_percent": ticker.get("price24hPcnt"),
                    "volume_24h": ticker.get("volume24h"),
                    "high_24h": ticker.get("highPrice24h"),
                    "low_24h": ticker.get("lowPrice24h")
                })
                found_symbols.append(ticker.get("symbol"))
        
        # Определяем не найденные символы
        not_found = [s for s in symbols if s not in found_symbols]
        
        result = {
            "category": category,
            "requested_symbols": symbols,
            "found_symbols": found_symbols,
            "not_found_symbols": not_found,
            "summary": filtered_tickers,
            "exchange": "Bybit"
        }
        
        logger.info(f"Сводка получена: найдено {len(found_symbols)} из {len(symbols)} символов")
        return json.dumps(result)
        
    except Exception as e:
        error_msg = f"Ошибка при получении сводки по символам: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "symbols_list": symbols_list, "category": category})