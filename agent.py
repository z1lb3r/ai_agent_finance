"""
Investment AI Agent - Using OpenAI Agents SDK.

This module implements the investment agent using OpenAI's Agents SDK,
with focus on SEC filing download and analysis functionality.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime

from openai import OpenAI
from agents import Agent, function_tool, set_default_openai_key, set_tracing_disabled
from agents.model_settings import ModelSettings

from config import (
    OPENAI_API_KEY, 
    DEFAULT_MODEL, 
    DEFAULT_TEMPERATURE
)
from prompts.investment_advisor import INVESTMENT_ADVISOR_PROMPT
from tools import sec_downloader
from tools import pdf_analyzer

# Устанавливаем API-ключ для Agents SDK
set_default_openai_key(OPENAI_API_KEY)

# Отключаем трассировку для устранения возможных ошибок
set_tracing_disabled(True)

# Настраиваем логгер
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("investment_agent")

# Регистрируем инструменты с помощью декоратора function_tool
@function_tool
def get_company_recent_filings(ticker: str, form_type: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Get a list of recent SEC filings for a company.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        form_type: The type of filing to retrieve (e.g., '10-K', '10-Q', '8-K')
        limit: Maximum number of filings to retrieve
    """
    try:
        # Если limit не указан, используем значение по умолчанию внутри функции
        actual_limit = 5 if limit is None else limit
        result = sec_downloader.search_filings(ticker, form_type, limit=actual_limit)
        summary = sec_downloader.get_filing_list_summary(result)
        return json.dumps({"result": summary, "filings_count": result.get("count", 0)})
    except Exception as e:
        logger.error(f"Error in get_company_recent_filings: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_company_quarterly_report(ticker: str, year: Optional[int] = None, quarter: Optional[int] = None) -> str:
    """
    Get the most recent quarterly report (10-Q) for a company or for a specific year and quarter.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        year: The specific year to search for
        quarter: The specific quarter (1-4) to search for (requires year to be specified)
    """
    try:
        if year:
            # Ищем отчет за конкретный год и квартал
            result = sec_downloader.search_filings_by_period(
                ticker, "10-Q", year, quarter, limit=1
            )
            
            if result.get("count", 0) == 0:
                period_desc = f"Q{quarter} {year}" if quarter else f"{year}"
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
            file_path = sec_downloader.download_filing_as_pdf(filing_url, output_filename)
            
            return json.dumps({
                "result": f"Downloaded 10-Q report for {ticker}",
                "filing_date": filed_date,
                "file_path": file_path
            })
        else:
            # Если год не указан, скачиваем самый свежий квартальный отчет
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-Q")
            
            if file_path.startswith("Error") or "error" in file_path.lower():
                return json.dumps({"error": file_path})
            
            return json.dumps({
                "result": f"Downloaded latest 10-Q report for {ticker}",
                "file_path": file_path
            })
    except Exception as e:
        logger.error(f"Error in get_company_quarterly_report: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_company_annual_report(ticker: str, year: Optional[int] = None) -> str:
    """
    Get the most recent annual report (10-K) for a company or for a specific year.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        year: The specific year to search for
    """
    try:
        if year:
            # Ищем отчет за конкретный год
            result = sec_downloader.search_filings_by_period(
                ticker, "10-K", year, None, limit=1
            )
            
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
            file_path = sec_downloader.download_filing_as_pdf(filing_url, output_filename)
            
            return json.dumps({
                "result": f"Downloaded 10-K report for {ticker} for {year}",
                "filing_date": filed_date,
                "file_path": file_path
            })
        else:
            # Если год не указан, скачиваем самый свежий годовой отчет
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-K")
            
            if file_path.startswith("Error") or "error" in file_path.lower():
                return json.dumps({"error": file_path})
            
            return json.dumps({
                "result": f"Downloaded latest 10-K report for {ticker}",
                "file_path": file_path
            })
    except Exception as e:
        logger.error(f"Error in get_company_annual_report: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def search_sec_filings(ticker: str, form_type: Optional[str] = None, 
                      start_date: Optional[str] = None, end_date: Optional[str] = None, 
                      limit: Optional[int] = None) -> str:
    """
    Search for SEC filings with custom filtering options.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        form_type: The type of filing to retrieve (e.g., '10-K', '10-Q', '8-K', 'DEF 14A')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of filings to retrieve
    """
    try:
        # Если limit не указан, используем значение по умолчанию
        actual_limit = 10 if limit is None else limit
        
        result = sec_downloader.search_filings(
            ticker, form_type, start_date, end_date, actual_limit
        )
        
        summary = sec_downloader.get_filing_list_summary(result)
        return json.dumps({
            "result": summary,
            "filings_count": result.get("count", 0),
            "ticker": ticker
        })
    except Exception as e:
        logger.error(f"Error in search_sec_filings: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def download_specific_filing(ticker: str, form_type: str, filing_index: Optional[int] = None) -> str:
    """
    Download a specific filing from search results.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        form_type: The type of filing to retrieve (e.g., '10-K', '10-Q', '8-K')
        filing_index: Index of the filing in search results (0 = most recent)
    """
    try:
        # Если индекс не указан, используем значение по умолчанию
        actual_index = 0 if filing_index is None else filing_index
        
        # Ищем отчеты
        result = sec_downloader.search_filings(ticker, form_type, limit=actual_index + 1)
        
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
        file_path = sec_downloader.download_filing_as_pdf(filing_url, output_filename)
        
        if file_path.startswith("Error") or "error" in file_path.lower():
            return json.dumps({"error": file_path})
        
        return json.dumps({
            "result": f"Downloaded {form_type} report for {ticker}",
            "filing_date": filed_date,
            "file_path": file_path,
            "filing_description": sec_downloader.format_filing_summary(filing)
        })
        
    except Exception as e:
        logger.error(f"Error in download_specific_filing: {str(e)}")
        return json.dumps({"error": str(e)})

# Новые инструменты для анализа PDF-отчетов

@function_tool
def extract_text_from_report(file_path: str) -> str:
    """
    Extract text content from a downloaded SEC report.
    
    Args:
        file_path: Path to the PDF file
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            return json.dumps({
                "error": f"File not found: {file_path}",
                "text": ""
            })
        
        # Извлекаем текст из PDF
        text = pdf_analyzer.extract_text_from_pdf(file_path)
        
        # Проверяем результат
        if text.startswith("Error:"):
            return json.dumps({
                "error": text,
                "text": ""
            })
        
        # Ограничиваем размер текста для возврата
        text_preview = text[:5000] + "..." if len(text) > 5000 else text
        
        return json.dumps({
            "result": f"Successfully extracted text from {os.path.basename(file_path)}",
            "text_preview": text_preview,
            "text_length": len(text),
            "file_path": file_path
        })
        
    except Exception as e:
        logger.error(f"Error in extract_text_from_report: {str(e)}")
        return json.dumps({"error": str(e), "text": ""})

@function_tool
def analyze_financial_report(file_path: str) -> str:
    """
    Analyze a financial report to extract key metrics and generate insights.
    
    Args:
        file_path: Path to the PDF file of the financial report
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            return json.dumps({
                "error": f"File not found: {file_path}",
                "analysis": {}
            })
        
        # Анализируем отчет
        analysis_result = pdf_analyzer.analyze_financial_report(file_path)
        
        if "error" in analysis_result:
            return json.dumps({
                "error": analysis_result["error"],
                "analysis": {}
            })
        
        # Создаем текстовое резюме для удобства
        summary = pdf_analyzer.summarize_report(analysis_result)
        
        return json.dumps({
            "result": f"Successfully analyzed {os.path.basename(file_path)}",
            "company_name": analysis_result.get("company_name", "Unknown"),
            "report_type": analysis_result.get("report_type", "Unknown"),
            "period": analysis_result.get("period", "Unknown"),
            "metrics": analysis_result.get("metrics", {}),
            "recommendations": analysis_result.get("recommendations", []),
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_financial_report: {str(e)}")
        return json.dumps({"error": str(e), "analysis": {}})

@function_tool
def extract_section_from_report(file_path: str, section_name: str) -> str:
    """
    Extract a specific section from a financial report.
    
    Args:
        file_path: Path to the PDF file
        section_name: Name of the section to extract (e.g., 'assets', 'liabilities', 'revenue', 'cash_flow')
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            return json.dumps({
                "error": f"File not found: {file_path}",
                "section": section_name
            })
        
        # Извлекаем определенный раздел
        section_data = pdf_analyzer.extract_specific_section(file_path, section_name)
        
        if "error" in section_data:
            return json.dumps({
                "error": section_data["error"],
                "section": section_name
            })
        
        return json.dumps({
            "result": f"Successfully extracted {section_name} section",
            "section": section_name,
            "content_preview": section_data.get("content", "")[:3000] + "..." if len(section_data.get("content", "")) > 3000 else section_data.get("content", ""),
            "numerical_data": section_data.get("numerical_data", []),
            "analysis": section_data.get("analysis", "")
        })
        
    except Exception as e:
        logger.error(f"Error in extract_section_from_report: {str(e)}")
        return json.dumps({"error": str(e), "section": section_name})

@function_tool
def get_and_analyze_latest_report(ticker: str, report_type: str) -> str:
    """
    Download the latest report for a company and analyze it in one step.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        report_type: Type of report to retrieve ('10-K' for annual or '10-Q' for quarterly)
    """
    try:
        # Проверяем тип отчета и используем значение по умолчанию внутри функции
        if report_type not in ["10-K", "10-Q"]:
            report_type = "10-Q"
            
        # Скачиваем последний отчет
        if report_type == "10-K":
            # Используем напрямую функции из sec_downloader вместо function_tools
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-K")
        else:  # Используем 10-Q
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-Q")
        
        if file_path.startswith("Error") or "error" in file_path.lower():
            return json.dumps({
                "error": file_path,
                "analysis": {}
            })
        
        if not file_path:
            return json.dumps({
                "error": "Failed to download report",
                "analysis": {}
            })
        
        # Анализируем скачанный отчет напрямую через pdf_analyzer
        analysis_result = pdf_analyzer.analyze_financial_report(file_path)
        
        if "error" in analysis_result:
            return json.dumps({
                "error": analysis_result["error"],
                "file_path": file_path,
                "analysis": {}
            })
        
        # Создаем текстовое резюме для удобства
        summary = pdf_analyzer.summarize_report(analysis_result)
        
        # Объединяем результаты
        result = {
            "result": f"Successfully downloaded and analyzed {report_type} report for {ticker}",
            "ticker": ticker,
            "report_type": report_type,
            "file_path": file_path,
            "company_name": analysis_result.get("company_name", "Unknown"),
            "report_type_detected": analysis_result.get("report_type", "Unknown"),
            "period": analysis_result.get("period", "Unknown"),
            "metrics": analysis_result.get("metrics", {}),
            "recommendations": analysis_result.get("recommendations", []),
            "summary": summary
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in get_and_analyze_latest_report: {str(e)}")
        return json.dumps({"error": str(e)})

@function_tool
def get_financial_summary(ticker: str, report_type: str) -> str:
    """
    Get a comprehensive financial summary from the latest company report.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        report_type: Type of report to analyze ('10-K' for annual or '10-Q' for quarterly)
    """
    try:
        # Проверяем тип отчета и используем значение по умолчанию внутри функции
        if report_type not in ["10-K", "10-Q"]:
            report_type = "10-Q"
            
        # Скачиваем последний отчет
        if report_type == "10-K":
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-K")
        else:
            file_path = sec_downloader.download_recent_filing_as_pdf(ticker, "10-Q")
        
        if file_path.startswith("Error") or "error" in file_path.lower():
            return json.dumps({
                "error": file_path,
                "summary": {}
            })
        
        if not file_path:
            return json.dumps({
                "error": "Failed to download report",
                "summary": {}
            })
        
        # Получаем базовый анализ
        analysis_result = pdf_analyzer.analyze_financial_report(file_path)
        
        # Извлекаем отдельные разделы для более детального анализа
        balance_sheet = pdf_analyzer.extract_specific_section(file_path, "balance_sheet")
        income_statement = pdf_analyzer.extract_specific_section(file_path, "income_statement")
        cash_flow = pdf_analyzer.extract_specific_section(file_path, "cash_flow")
        
        # Дополнительно извлекаем детальные данные из конкретных разделов
        assets_data = pdf_analyzer.extract_specific_section(file_path, "assets")
        liabilities_data = pdf_analyzer.extract_specific_section(file_path, "liabilities")
        equity_data = pdf_analyzer.extract_specific_section(file_path, "equity")
        revenue_data = pdf_analyzer.extract_specific_section(file_path, "revenue")
        income_data = pdf_analyzer.extract_specific_section(file_path, "income")
        
        # Компилируем все показатели в единую структуру
        all_numerical_data = []
        
        # Объединяем числовые данные из всех разделов
        sections_with_data = [
            balance_sheet, income_statement, cash_flow,
            assets_data, liabilities_data, equity_data,
            revenue_data, income_data
        ]
        
        for section in sections_with_data:
            if isinstance(section, dict) and "numerical_data" in section:
                all_numerical_data.extend(section.get("numerical_data", []))
        
        # Удаляем дубликаты по описанию
        unique_data = {}
        for item in all_numerical_data:
            desc = item["description"].lower().strip()
            if desc not in unique_data or (desc in unique_data and item.get("confidence", "low") > unique_data[desc].get("confidence", "low")):
                unique_data[desc] = item
        
        # Структурируем финансовые показатели по категориям
        categorized_metrics = {
            "Общие показатели": {},
            "Балансовые показатели": {},
            "Доходы и расходы": {},
            "Денежные потоки": {},
            "Коэффициенты и соотношения": {},
        }
        
        # Распределяем показатели по категориям
        for desc, item in unique_data.items():
            value = item["value"]
            category = "Общие показатели"
            
            # Определяем категорию на основе описания
            if any(word in desc for word in ["asset", "cash", "receivable", "inventory", "property", "equipment", "goodwill"]):
                category = "Балансовые показатели"
            elif any(word in desc for word in ["liability", "debt", "payable", "loan", "borrowing", "obligation"]):
                category = "Балансовые показатели"
            elif any(word in desc for word in ["equity", "capital", "stock", "retained", "earnings", "dividend"]):
                category = "Балансовые показатели"
            elif any(word in desc for word in ["revenue", "sales", "cost", "expense", "income", "profit", "margin", "earnings", "eps"]):
                category = "Доходы и расходы"
            elif any(word in desc for word in ["cash flow", "operating activities", "investing activities", "financing activities"]):
                category = "Денежные потоки"
            elif any(word in desc for word in ["ratio", "percent", "return", "roe", "roa", "ebitda", "margin"]):
                category = "Коэффициенты и соотношения"
            
            categorized_metrics[category][desc] = value
        
        # Создаем итоговый отчет
        company_name = analysis_result.get("company_name", ticker)
        report_period = analysis_result.get("period", "последний отчетный период")
        metrics = analysis_result.get("metrics", {})
        
        # Объединяем все данные в итоговый результат
        summary = {
            "ticker": ticker,
            "company_name": company_name,
            "report_type": report_type,
            "report_period": report_period,
            "file_path": file_path,
            "metrics": metrics,
            "financial_position": {
                "balance_sheet_summary": balance_sheet.get("analysis", ""),
                "income_statement_summary": income_statement.get("analysis", ""),
                "cash_flow_summary": cash_flow.get("analysis", ""),
                "assets_data": assets_data.get("numerical_data", [])[:10],  # Ограничиваем количество элементов
                "liabilities_data": liabilities_data.get("numerical_data", [])[:10],
                "equity_data": equity_data.get("numerical_data", [])[:5],
                "revenue_data": revenue_data.get("numerical_data", [])[:5],
                "income_data": income_data.get("numerical_data", [])[:5]
            },
            "categorized_metrics": categorized_metrics,
            "section_analyses": {
                "assets": assets_data.get("analysis", ""),
                "liabilities": liabilities_data.get("analysis", ""),
                "equity": equity_data.get("analysis", ""),
                "revenue": revenue_data.get("analysis", ""),
                "income": income_data.get("analysis", "")
            }
        }
        
        return json.dumps(summary)
        
    except Exception as e:
        logger.error(f"Error in get_financial_summary: {str(e)}")
        return json.dumps({"error": str(e)})

# Создаем настройки модели
model_settings = ModelSettings(temperature=DEFAULT_TEMPERATURE)

# Создаем экземпляр агента с обновленным набором инструментов
investment_agent = Agent(
    name="InvestmentAdvisor",
    instructions=INVESTMENT_ADVISOR_PROMPT,
    model=DEFAULT_MODEL,
    model_settings=model_settings,
    tools=[
        # Инструменты для работы с SEC EDGAR
        get_company_recent_filings,
        get_company_quarterly_report,
        get_company_annual_report,
        search_sec_filings,
        download_specific_filing,
        
        # Инструменты для анализа отчетов
        extract_text_from_report,
        analyze_financial_report,
        get_and_analyze_latest_report,
        extract_section_from_report,
        get_financial_summary  # Новая функция для комплексного анализа
    ]
)

logger.info("Investment Agent created successfully with SEC filing tools and analysis capabilities")