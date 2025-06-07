"""
Trade Tracker - Инструмент для учета и анализа торговых сделок

Этот модуль предоставляет функциональность для:
1. Создания и ведения базы данных сделок
2. Добавления новых сделок
3. Обновления существующих сделок
4. Получения статистики и аналитики по сделкам
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum

# Импортируем регистратор инструментов
from .registry import register_tool

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trade_tracker")

# Константы
# Определяем путь к базе данных относительно текущего файла
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trades.db")
logger.info(f"Using database at: {DB_PATH}")

# Определяем типы сделок для ясности
class PositionType(str, Enum):
    LONG = "long"
    SHORT = "short"

class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"

def init_database() -> None:
    """
    Инициализирует базу данных сделок, если она не существует.
    """
    # Убеждаемся, что директория для базы данных существует
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy TEXT NOT NULL,
        trade_type TEXT NOT NULL,  -- тип сделки (акции, опционы, фьючерсы и т.д.)
        instrument TEXT NOT NULL,  -- тикер или название инструмента
        position_type TEXT NOT NULL,  -- LONG или SHORT
        quantity REAL NOT NULL,
        open_date TEXT NOT NULL,
        open_price REAL NOT NULL,
        close_date TEXT,           -- может быть NULL для открытых позиций
        close_price REAL,          -- может быть NULL для открытых позиций
        profit_percent REAL,       -- может быть NULL для открытых позиций
        profit_amount REAL,        -- может быть NULL для открытых позиций
        status TEXT NOT NULL       -- OPEN или CLOSED
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info(f"База данных сделок инициализирована по пути: {DB_PATH}")

# Инициализируем базу данных при импорте модуля
init_database()

@register_tool
def add_trade(strategy: str, trade_type: str, instrument: str, 
              position_type: str, quantity: float, open_date: str, 
              open_price: float) -> str:
    """
    Добавляет новую открытую сделку в базу данных.
    
    Args:
        strategy: Торговая стратегия (например, 'Momentum', 'Value')
        trade_type: Тип сделки (например, 'Stocks', 'Options', 'Futures')
        instrument: Тикер или название инструмента (например, 'AAPL')
        position_type: Тип позиции ('long' или 'short')
        quantity: Количество купленного/проданного инструмента
        open_date: Дата открытия позиции в формате YYYY-MM-DD
        open_price: Цена покупки/продажи инструмента
        
    Returns:
        JSON строка с информацией о добавленной сделке
    """
    try:
        # Проверка позиции на валидность
        if position_type.lower() not in [PositionType.LONG, PositionType.SHORT]:
            return json.dumps({
                "error": f"Недопустимый тип позиции: {position_type}. Используйте 'long' или 'short'."
            })
        
        # Проверка даты
        try:
            datetime.strptime(open_date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({
                "error": f"Неверный формат даты: {open_date}. Используйте формат YYYY-MM-DD."
            })
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO trades (
            strategy, trade_type, instrument, position_type,
            quantity, open_date, open_price, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy, trade_type, instrument, position_type.lower(),
            quantity, open_date, open_price, TradeStatus.OPEN
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return json.dumps({
            "success": True,
            "message": f"Сделка #{trade_id} успешно добавлена",
            "trade_id": trade_id,
            "trade_details": {
                "strategy": strategy,
                "trade_type": trade_type,
                "instrument": instrument,
                "position_type": position_type,
                "quantity": quantity,
                "open_date": open_date,
                "open_price": open_price,
                "status": TradeStatus.OPEN
            }
        })
    
    except Exception as e:
        logger.error(f"Ошибка при добавлении сделки: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def close_trade(trade_id: int, close_date: str, close_price: float) -> str:
    """
    Закрывает существующую сделку, вычисляя прибыль/убыток.
    
    Args:
        trade_id: ID сделки для закрытия
        close_date: Дата закрытия позиции в формате YYYY-MM-DD
        close_price: Цена закрытия позиции
        
    Returns:
        JSON строка с информацией о закрытой сделке
    """
    try:
        # Проверка даты
        try:
            datetime.strptime(close_date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({
                "error": f"Неверный формат даты: {close_date}. Используйте формат YYYY-MM-DD."
            })
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем информацию о сделке
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        if not trade:
            conn.close()
            return json.dumps({"error": f"Сделка с ID {trade_id} не найдена"})
        
        # Получаем данные сделки
        (id, strategy, trade_type, instrument, position_type, 
         quantity, open_date, open_price, _, _, _, _, status) = trade
        
        if status == TradeStatus.CLOSED:
            conn.close()
            return json.dumps({"error": f"Сделка с ID {trade_id} уже закрыта"})
        
        # Вычисляем прибыль/убыток
        if position_type == PositionType.LONG:
            # Для длинных позиций: (цена закрытия - цена открытия) / цена открытия * 100%
            profit_percent = (close_price - open_price) / open_price * 100
            profit_amount = (close_price - open_price) * quantity
        else:  # SHORT
            # Для коротких позиций: (цена открытия - цена закрытия) / цена открытия * 100%
            profit_percent = (open_price - close_price) / open_price * 100
            profit_amount = (open_price - close_price) * quantity
        
        # Обновляем запись в базе данных
        cursor.execute('''
        UPDATE trades 
        SET close_date = ?, close_price = ?, profit_percent = ?, 
            profit_amount = ?, status = ?
        WHERE id = ?
        ''', (
            close_date, close_price, profit_percent, 
            profit_amount, TradeStatus.CLOSED, trade_id
        ))
        
        conn.commit()
        conn.close()
        
        return json.dumps({
            "success": True,
            "message": f"Сделка #{trade_id} успешно закрыта",
            "trade_id": trade_id,
            "trade_details": {
                "strategy": strategy,
                "trade_type": trade_type,
                "instrument": instrument,
                "position_type": position_type,
                "quantity": quantity,
                "open_date": open_date,
                "open_price": open_price,
                "close_date": close_date,
                "close_price": close_price,
                "profit_percent": round(profit_percent, 2),
                "profit_amount": round(profit_amount, 2),
                "status": TradeStatus.CLOSED
            }
        })
    
    except Exception as e:
        logger.error(f"Ошибка при закрытии сделки: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def get_trade(trade_id: int) -> str:
    """
    Получает информацию о конкретной сделке.
    
    Args:
        trade_id: ID сделки
        
    Returns:
        JSON строка с информацией о сделке
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Чтобы получить результат в виде словаря
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        conn.close()
        
        if not trade:
            return json.dumps({"error": f"Сделка с ID {trade_id} не найдена"})
        
        # Преобразуем Row в словарь
        trade_dict = dict(trade)
        
        return json.dumps({
            "success": True,
            "trade": trade_dict
        })
    
    except Exception as e:
        logger.error(f"Ошибка при получении сделки: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def list_trades(status: Optional[str] = None, instrument: Optional[str] = None, 
               strategy: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Возвращает список сделок с возможностью фильтрации.
    
    Args:
        status: Фильтр по статусу сделки ('open' или 'closed')
        instrument: Фильтр по инструменту
        strategy: Фильтр по стратегии
        limit: Максимальное количество возвращаемых сделок
        
    Returns:
        JSON строка со списком сделок
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM trades'
        params = []
        where_clauses = []
        
        if status:
            where_clauses.append('status = ?')
            params.append(status)
        
        if instrument:
            where_clauses.append('instrument = ?')
            params.append(instrument)
        
        if strategy:
            where_clauses.append('strategy = ?')
            params.append(strategy)
        
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
        
        query += ' ORDER BY id DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        trades = cursor.fetchall()
        
        conn.close()
        
        # Преобразуем список Row в список словарей
        trades_list = [dict(trade) for trade in trades]
        
        return json.dumps({
            "success": True,
            "trades_count": len(trades_list),
            "trades": trades_list
        })
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка сделок: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def get_trade_statistics(period: Optional[str] = None, 
                        strategy: Optional[str] = None) -> str:
    """
    Возвращает статистику по сделкам.
    
    Args:
        period: Период для анализа ('month', 'quarter', 'year', 'all')
        strategy: Фильтр по стратегии
        
    Returns:
        JSON строка со статистикой по сделкам
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Определяем фильтр по дате в зависимости от периода
        date_filter = ''
        if period:
            today = datetime.now().strftime('%Y-%m-%d')
            if period == 'month':
                date_filter = f" AND open_date >= date('{today}', '-1 month')"
            elif period == 'quarter':
                date_filter = f" AND open_date >= date('{today}', '-3 month')"
            elif period == 'year':
                date_filter = f" AND open_date >= date('{today}', '-1 year')"
        
        # Создаем фильтр по стратегии
        strategy_filter = f" AND strategy = '{strategy}'" if strategy else ""
        
        # Получаем общее количество сделок
        cursor.execute(
            f'SELECT COUNT(*) FROM trades WHERE 1=1 {date_filter} {strategy_filter}'
        )
        total_trades = cursor.fetchone()[0]
        
        # Получаем количество прибыльных сделок
        cursor.execute(
            f'SELECT COUNT(*) FROM trades WHERE profit_amount > 0 AND status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        profitable_trades = cursor.fetchone()[0]
        
        # Получаем количество убыточных сделок
        cursor.execute(
            f'SELECT COUNT(*) FROM trades WHERE profit_amount < 0 AND status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        losing_trades = cursor.fetchone()[0]
        
        # Получаем общую прибыль
        cursor.execute(
            f'SELECT SUM(profit_amount) FROM trades WHERE status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        total_profit = cursor.fetchone()[0] or 0
        
        # Получаем среднюю прибыль на сделку
        cursor.execute(
            f'SELECT AVG(profit_amount) FROM trades WHERE status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        avg_profit = cursor.fetchone()[0] or 0
        
        # Получаем среднюю прибыль в процентах
        cursor.execute(
            f'SELECT AVG(profit_percent) FROM trades WHERE status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        avg_profit_percent = cursor.fetchone()[0] or 0
        
        # Получаем максимальную прибыль
        cursor.execute(
            f'SELECT MAX(profit_amount) FROM trades WHERE status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        max_profit = cursor.fetchone()[0] or 0
        
        # Получаем максимальный убыток
        cursor.execute(
            f'SELECT MIN(profit_amount) FROM trades WHERE status = ? {date_filter} {strategy_filter}',
            (TradeStatus.CLOSED,)
        )
        max_loss = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Рассчитываем процент успешных сделок
        closed_trades = profitable_trades + losing_trades
        win_rate = (profitable_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        statistics = {
            "total_trades": total_trades,
            "closed_trades": closed_trades,
            "open_trades": total_trades - closed_trades,
            "profitable_trades": profitable_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit": round(avg_profit, 2),
            "avg_profit_percent": round(avg_profit_percent, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(max_loss, 2)
        }
        
        return json.dumps({
            "success": True,
            "period": period or "all",
            "strategy": strategy or "all",
            "statistics": statistics
        })
    
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        return json.dumps({"error": str(e)})

@register_tool
def get_trade_form_questions() -> str:
    """
    Возвращает список вопросов для заполнения формы добавления новой сделки.
    
    Returns:
        JSON строка с вопросами для формы
    """
    questions = [
        {
            "field": "strategy",
            "question": "Какую стратегию вы использовали для этой сделки?",
            "type": "text",
            "examples": ["Momentum", "Value", "Swing", "Day Trading"]
        },
        {
            "field": "trade_type",
            "question": "Какой тип инструмента вы торговали?",
            "type": "text",
            "examples": ["Stocks", "Options", "Futures", "Forex", "Crypto"]
        },
        {
            "field": "instrument",
            "question": "Какой тикер или название инструмента?",
            "type": "text",
            "examples": ["AAPL", "TSLA", "BTC/USD"]
        },
        {
            "field": "position_type",
            "question": "Вы открыли длинную (long) или короткую (short) позицию?",
            "type": "choice",
            "options": ["long", "short"]
        },
        {
            "field": "quantity",
            "question": "Какое количество инструмента вы купили/продали?",
            "type": "number",
            "examples": ["100", "0.5", "10"]
        },
        {
            "field": "open_date",
            "question": "Когда вы открыли позицию? (формат YYYY-MM-DD)",
            "type": "date",
            "examples": [datetime.now().strftime("%Y-%m-%d")]
        },
        {
            "field": "open_price",
            "question": "По какой цене вы открыли позицию?",
            "type": "number",
            "examples": ["150.25", "0.00023", "4200.50"]
        }
    ]
    
    return json.dumps({
        "success": True,
        "form_title": "Добавление новой сделки",
        "questions": questions
    })

@register_tool
def get_close_trade_form_questions() -> str:
    """
    Возвращает список вопросов для заполнения формы закрытия сделки.
    
    Returns:
        JSON строка с вопросами для формы
    """
    questions = [
        {
            "field": "trade_id",
            "question": "Введите ID сделки, которую хотите закрыть:",
            "type": "number"
        },
        {
            "field": "close_date",
            "question": "Когда вы закрыли позицию? (формат YYYY-MM-DD)",
            "type": "date",
            "examples": [datetime.now().strftime("%Y-%m-%d")]
        },
        {
            "field": "close_price",
            "question": "По какой цене вы закрыли позицию?",
            "type": "number"
        }
    ]
    
    return json.dumps({
        "success": True,
        "form_title": "Закрытие сделки",
        "questions": questions
    })