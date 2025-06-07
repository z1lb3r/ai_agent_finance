"""
PDF Analyzer - Инструмент для извлечения и анализа содержимого финансовых отчетов в формате PDF.

Этот модуль предоставляет функции для:
1. Извлечения текста из PDF-файлов
2. Структурирования финансовой информации
3. Анализа ключевых показателей
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

# Импортируем регистратор инструментов
from .registry import register_tool

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pdf_analyzer")

# Пытаемся импортировать различные библиотеки для работы с PDF
# в порядке предпочтения и доступности
pdf_extractor = None
pdf_extraction_method = None

try:
    import fitz  # PyMuPDF
    pdf_extractor = fitz
    pdf_extraction_method = "pymupdf"
    logger.info("Using PyMuPDF for PDF extraction")
except ImportError:
    try:
        from pdfminer.high_level import extract_text
        pdf_extractor = extract_text
        pdf_extraction_method = "pdfminer"
        logger.info("Using PDFMiner for PDF extraction")
    except ImportError:
        try:
            import PyPDF2
            pdf_extractor = PyPDF2
            pdf_extraction_method = "pypdf2"
            logger.info("Using PyPDF2 for PDF extraction")
        except ImportError:
            logger.warning("No PDF extraction library found. Install PyMuPDF, PDFMiner, or PyPDF2.")

@register_tool
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Извлекает текст из PDF-файла используя доступную библиотеку.
    
    Args:
        pdf_path: Путь к PDF-файлу
        
    Returns:
        JSON строка с результатами извлечения текста
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return json.dumps({"error": f"File not found at {pdf_path}", "text": ""})
    
    # Обработка путей формата "sandbox:..."
    clean_path = pdf_path
    if pdf_path.startswith("sandbox:"):
        clean_path = pdf_path[9:]  # Удаляем префикс "sandbox:"
    
    try:
        text = ""
        logger.info(f"Начинаем извлечение текста из {clean_path}")
        
        if pdf_extraction_method == "pymupdf":
            try:
                with fitz.open(clean_path) as doc:
                    for page in doc:
                        text += page.get_text()
            except Exception as e:
                logger.error(f"Error extracting text with PyMuPDF: {str(e)}")
        
        if not text and pdf_extraction_method == "pdfminer":
            try:
                text = extract_text(clean_path)
            except Exception as e:
                logger.error(f"Error extracting text with PDFMiner: {str(e)}")
        
        if not text and pdf_extraction_method == "pypdf2":
            try:
                with open(clean_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text
            except Exception as e:
                logger.error(f"Error extracting text with PyPDF2: {str(e)}")
        
        if not text:
            return json.dumps({"error": "Failed to extract text from PDF", "text": ""})
        
        return json.dumps({
            "text": text,
            "text_length": len(text),
            "file_path": pdf_path
        })
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return json.dumps({"error": f"Error extracting text: {str(e)}", "text": ""})

# Эта функция не будет декорирована @register_tool
def extract_numerical_data_enhanced(text: str) -> List[Dict]:
    """
    Усовершенствованное извлечение числовых данных из текста с улучшенным сопоставлением описаний.
    
    Args:
        text: Текст для анализа
        
    Returns:
        Список словарей с описаниями и числовыми значениями
    """
    results = []
    
    # Базовый паттерн для чисел с денежными знаками
    # Ищет строки вида "Cash and cash equivalents ... $1,234.56 million" или "Revenue: $1,234.56"
    money_pattern = r'([A-Za-z\s\-,\(\)]{5,100})[:\.\s]+[\$\€\£]?\s*([\d,\.]+)\s*(?:million|billion|thousand|M|B|K)?'
    
    # Паттерн для таблиц с числами (без символов валют)
    # Ищет строки вида "Cash and cash equivalents ... 1,234.56" или "Revenue: 1,234.56"
    table_pattern = r'([A-Za-z\s\-,\(\)]{5,100})[:\.\s]+([\d,\.]+)\s*(?:million|billion|thousand|M|B|K)?'
    
    # Ищем явные денежные значения
    money_matches = re.findall(money_pattern, text)
    for desc, value in money_matches:
        try:
            # Очищаем и форматируем данные
            desc = desc.strip()
            value_clean = value.replace(',', '')
            
            # Пытаемся преобразовать в число
            numeric_value = float(value_clean)
            
            # Определяем множитель если указан (million, billion и т.д.)
            multiplier = 1
            if "million" in text[text.find(value):text.find(value) + 30].lower():
                multiplier = 1000000
            elif "billion" in text[text.find(value):text.find(value) + 30].lower():
                multiplier = 1000000000
            elif "thousand" in text[text.find(value):text.find(value) + 30].lower() or "K" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000
            elif "M" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000000
            elif "B" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000000000
                
            # Применяем множитель
            numeric_value *= multiplier
            
            results.append({
                "description": desc,
                "value": numeric_value,
                "raw_value": value,
                "confidence": "high" if "$" in text[text.find(desc):text.find(value)] else "medium"
            })
        except ValueError:
            # Пропускаем, если не удалось преобразовать в число
            pass
    
    # Ищем табличные числовые значения без символов валют
    table_matches = re.findall(table_pattern, text)
    for desc, value in table_matches:
        # Пропускаем уже найденные совпадения
        if any(d["description"] == desc.strip() for d in results):
            continue
            
        try:
            # Очищаем и форматируем данные
            desc = desc.strip()
            value_clean = value.replace(',', '')
            
            # Пытаемся преобразовать в число
            numeric_value = float(value_clean)
            
            # Определяем множитель если указан (million, billion и т.д.)
            multiplier = 1
            if "million" in text[text.find(value):text.find(value) + 30].lower():
                multiplier = 1000000
            elif "billion" in text[text.find(value):text.find(value) + 30].lower():
                multiplier = 1000000000
            elif "thousand" in text[text.find(value):text.find(value) + 30].lower() or "K" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000
            elif "M" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000000
            elif "B" in text[text.find(value):text.find(value) + 5]:
                multiplier = 1000000000
                
            # Применяем множитель
            numeric_value *= multiplier
            
            results.append({
                "description": desc,
                "value": numeric_value,
                "raw_value": value,
                "confidence": "medium"
            })
        except ValueError:
            # Пропускаем, если не удалось преобразовать в число
            pass
    
    # Сортируем результаты по убыванию уверенности и значимости описания
    return sorted(
        results, 
        key=lambda x: (
            0 if x["confidence"] == "high" else 1 if x["confidence"] == "medium" else 2,
            0 if any(key in x["description"].lower() for key in ["total", "net", "revenue", "income", "assets", "liabilities"]) else 1
        )
    )

# Эта функция не будет декорирована @register_tool
def analyze_section_content(section_name: str, content: str, numerical_data: List[Dict]) -> str:
    """
    Анализирует содержимое раздела и создает структурированное описание.
    
    Args:
        section_name: Название раздела
        content: Содержимое раздела
        numerical_data: Найденные числовые данные
        
    Returns:
        Текстовый анализ раздела
    """
    analysis = []
    
    # Базовое описание раздела
    if section_name.lower() == "assets":
        analysis.append("Анализ активов компании:")
    elif section_name.lower() == "liabilities":
        analysis.append("Анализ обязательств компании:")
    elif section_name.lower() == "equity":
        analysis.append("Анализ собственного капитала компании:")
    elif section_name.lower() == "revenue":
        analysis.append("Анализ выручки компании:")
    elif section_name.lower() == "income":
        analysis.append("Анализ прибыли компании:")
    elif section_name.lower() == "cash_flow":
        analysis.append("Анализ денежных потоков компании:")
    elif section_name.lower() == "balance_sheet":
        analysis.append("Анализ баланса компании:")
    elif section_name.lower() == "income_statement":
        analysis.append("Анализ отчета о прибылях и убытках:")
    else:
        analysis.append(f"Анализ раздела '{section_name}':")
    
    # Анализ найденных числовых данных
    if numerical_data:
        # Структурируем данные по категориям
        categorized_data = {}
        
        for item in numerical_data:
            # Определяем категорию на основе описания
            category = "Другое"
            desc = item["description"].lower()
            
            if section_name.lower() == "assets" or section_name.lower() == "balance_sheet":
                if "total assets" in desc:
                    category = "Всего активов"
                elif "current assets" in desc:
                    category = "Текущие активы"
                elif "cash" in desc or "equivalent" in desc:
                    category = "Денежные средства"
                elif "receivable" in desc:
                    category = "Дебиторская задолженность"
                elif "inventory" in desc:
                    category = "Запасы"
                elif "property" in desc or "equipment" in desc or "ppe" in desc:
                    category = "Основные средства"
                elif "goodwill" in desc or "intangible" in desc:
                    category = "Нематериальные активы"
            
            elif section_name.lower() == "liabilities" or section_name.lower() == "balance_sheet":
                if "total liabilities" in desc:
                    category = "Всего обязательств"
                elif "current liabilities" in desc:
                    category = "Текущие обязательства"
                elif "long-term" in desc or "longterm" in desc:
                    category = "Долгосрочные обязательства"
                elif "debt" in desc or "borrowing" in desc or "loan" in desc:
                    category = "Долг"
                elif "payable" in desc:
                    category = "Кредиторская задолженность"
            
            elif section_name.lower() == "income" or section_name.lower() == "income_statement":
                if "revenue" in desc or "sales" in desc:
                    category = "Выручка"
                elif "gross" in desc and ("profit" in desc or "margin" in desc):
                    category = "Валовая прибыль"
                elif "operating" in desc and ("income" in desc or "profit" in desc):
                    category = "Операционная прибыль"
                elif "net" in desc and ("income" in desc or "profit" in desc or "earnings" in desc):
                    category = "Чистая прибыль"
                elif "eps" in desc or "earnings per share" in desc:
                    category = "Прибыль на акцию"
            
            elif section_name.lower() == "cash_flow":
                if "operating" in desc:
                    category = "Операционный денежный поток"
                elif "investing" in desc:
                    category = "Инвестиционный денежный поток"
                elif "financing" in desc:
                    category = "Финансовый денежный поток"
                elif "free cash flow" in desc:
                    category = "Свободный денежный поток"
                elif "cash and cash equivalent" in desc:
                    category = "Денежные средства и эквиваленты"
            
            # Группируем данные по категориям
            if category not in categorized_data:
                categorized_data[category] = []
            
            categorized_data[category].append(item)
        
        # Добавляем сводку по категориям
        for category, items in categorized_data.items():
            if category != "Другое":
                analysis.append(f"\n{category}:")
                for item in items[:3]:  # Берем только первые 3 элемента в каждой категории
                    formatted_value = f"${item['value']:,.0f}" if item['value'] >= 1000 else f"${item['value']:,.2f}"
                    analysis.append(f"- {item['description']}: {formatted_value}")
        
        # Добавляем прочие значимые показатели
        if "Другое" in categorized_data and categorized_data["Другое"]:
            important_items = [
                item for item in categorized_data["Другое"] 
                if any(key in item["description"].lower() for key in ["total", "net", "ebitda", "margin", "ratio"])
            ]
            
            if important_items:
                analysis.append("\nДругие важные показатели:")
                for item in important_items[:5]:  # Ограничиваем количество
                    formatted_value = f"${item['value']:,.0f}" if item['value'] >= 1000 else f"${item['value']:,.2f}"
                    analysis.append(f"- {item['description']}: {formatted_value}")
    else:
        analysis.append("Не удалось извлечь структурированные числовые данные из этого раздела.")
    
    # Общий вывод
    if len(numerical_data) > 0:
        analysis.append(f"\nВсего найдено {len(numerical_data)} числовых показателей в разделе.")
    
    return "\n".join(analysis)

@register_tool
def find_financial_tables(text: str) -> str:
    """
    Ищет и извлекает разделы с финансовыми таблицами из текста отчета.
    
    Args:
        text: Текст отчета
        
    Returns:
        JSON строка с найденными разделами финансовой отчетности
    """
    sections = {}
    
    # Ключевые разделы и их заголовки
    section_patterns = {
        "income_statement": r"(consolidated\s+statements?\s+of\s+(?:income|operations|earnings)|statements?\s+of\s+(?:income|operations|earnings))",
        "balance_sheet": r"(consolidated\s+balance\s+sheets?|balance\s+sheets?)",
        "cash_flow": r"(consolidated\s+statements?\s+of\s+cash\s+flows?|statements?\s+of\s+cash\s+flows?)",
        "stockholders_equity": r"(consolidated\s+statements?\s+of\s+(?:stockholders'?|shareholders'?)\s+equity|statements?\s+of\s+(?:stockholders'?|shareholders'?)\s+equity)"
    }
    
    for section_name, pattern in section_patterns.items():
        # Поиск разделов с использованием регулярных выражений
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        if matches:
            # Примерно определяем начало и конец раздела
            start_idx = matches[0].start()
            
            # Ищем следующий раздел или конец документа
            end_idx = len(text)
            for other_pattern in section_patterns.values():
                if other_pattern != pattern:
                    other_matches = list(re.finditer(other_pattern, text[start_idx+1000:], re.IGNORECASE))
                    if other_matches:
                        potential_end = start_idx + 1000 + other_matches[0].start()
                        if potential_end < end_idx:
                            end_idx = potential_end
            
            # Извлекаем содержимое раздела
            section_content = text[start_idx:end_idx].strip()
            sections[section_name] = section_content
    
    return json.dumps(sections)

@register_tool
def extract_key_metrics(text: str) -> str:
    """
    Извлекает ключевые финансовые метрики из текста отчета.
    
    Args:
        text: Текст отчета
        
    Returns:
        JSON строка с извлеченными метриками
    """
    metrics = {}
    
    # Поиск выручки (Revenue)
    revenue_patterns = [
        r"(?:total\s+)?revenue[s]?[\s\:]+[\$\s]*([\d,\.]+)(?:\s*million|\s*billion)?",
        r"net\s+revenue[s]?[\s\:]+[\$\s]*([\d,\.]+)(?:\s*million|\s*billion)?"
    ]
    
    for pattern in revenue_patterns:
        revenue_match = re.search(pattern, text, re.IGNORECASE)
        if revenue_match:
            revenue_str = revenue_match.group(1).replace(",", "")
            try:
                metrics["revenue"] = float(revenue_str)
                break
            except ValueError:
                pass
    
    # Поиск чистой прибыли (Net Income)
    net_income_patterns = [
        r"net\s+income[\s\:]+[\$\s]*([\d,\.]+)(?:\s*million|\s*billion)?",
        r"income\s+(?:before|after)\s+(?:income\s+)?tax(?:es)?[\s\:]+[\$\s]*([\d,\.]+)(?:\s*million|\s*billion)?"
    ]
    
    for pattern in net_income_patterns:
        net_income_match = re.search(pattern, text, re.IGNORECASE)
        if net_income_match:
            net_income_str = net_income_match.group(1).replace(",", "")
            try:
                metrics["net_income"] = float(net_income_str)
                break
            except ValueError:
                pass
    
    # Поиск EPS (Earnings Per Share)
    eps_patterns = [
        r"(?:diluted\s+)?earnings\s+per\s+(?:common\s+)?share[\s\:]+[\$\s]*([\d,\.]+)",
        r"(?:basic\s+)?earnings\s+per\s+(?:common\s+)?share[\s\:]+[\$\s]*([\d,\.]+)"
    ]
    
    for pattern in eps_patterns:
        eps_match = re.search(pattern, text, re.IGNORECASE)
        if eps_match:
            eps_str = eps_match.group(1).replace(",", "")
            try:
                metrics["eps"] = float(eps_str)
                break
            except ValueError:
                pass
    
    return json.dumps(metrics)

@register_tool
def analyze_financial_report(pdf_path: str) -> str:
    """
    Анализирует финансовый отчет и возвращает структурированные данные.
    
    Args:
        pdf_path: Путь к PDF-файлу с отчетом
        
    Returns:
        JSON строка с результатами анализа
    """
    if not pdf_extractor:
        return json.dumps({
            "error": "No PDF extraction library available. Install PyMuPDF, PDFMiner, or PyPDF2."
        })
    
    # Обработка путей формата "sandbox:..."
    clean_path = pdf_path
    if pdf_path.startswith("sandbox:"):
        clean_path = pdf_path[9:]  # Удаляем префикс "sandbox:"
    
    # Проверяем существование файла
    if not os.path.exists(clean_path):
        logger.error(f"PDF file not found: {clean_path}")
        return json.dumps({
            "error": f"File not found: {clean_path}"
        })
    
    # Извлекаем текст из PDF
    try:
        text_result = json.loads(extract_text_from_pdf(pdf_path))
        
        if "error" in text_result:
            return json.dumps({
                "error": text_result["error"]
            })
            
        text = text_result.get("text", "")
        if not text:
            return json.dumps({
                "error": "No text extracted from PDF"
            })
        
        # Определяем тип отчета
        report_type = "unknown"
        if re.search(r"form\s+10-k", text, re.IGNORECASE):
            report_type = "10-K"
        elif re.search(r"form\s+10-q", text, re.IGNORECASE):
            report_type = "10-Q"
        elif re.search(r"form\s+8-k", text, re.IGNORECASE):
            report_type = "8-K"
        
        # Ищем период отчета
        period_match = re.search(r"(?:quarter|period|year)[\s\w]+end(?:ed|ing)\s+(\w+\s+\d{1,2},?\s+\d{4})", text, re.IGNORECASE)
        period = period_match.group(1) if period_match else "unknown"
        
        # Ищем имя компании
        company_match = re.search(r"([\w\s,\.]+)(?:\(|is\s+a)", text[:1000], re.IGNORECASE)
        company_name = company_match.group(1).strip() if company_match else "unknown"
        
        # Извлекаем финансовые таблицы
        financial_sections = json.loads(find_financial_tables(text))
        
        # Извлекаем ключевые метрики
        metrics = json.loads(extract_key_metrics(text))
        
        # Анализируем MD&A раздел для получения качественных показателей
        mda_match = re.search(r"(?:item\s+[27][\.\):]|management\'s\s+discussion\s+and\s+analysis).{0,200}(.*?)(?:item\s+[38][\.\)]|subsequent\s+events)", text, re.IGNORECASE | re.DOTALL)
        management_discussion = mda_match.group(1) if mda_match else ""
        
        # Извлекаем основные факторы, влияющие на бизнес
        risk_factors_match = re.search(r"(?:item\s+1a[\.\):]|risk\s+factors).{0,200}(.*?)(?:item\s+[12][\.\)]|unresolved\s+staff\s+comments)", text, re.IGNORECASE | re.DOTALL)
        risk_factors = risk_factors_match.group(1) if risk_factors_match else ""
        
        # Генерируем рекомендации
        recommendations = []
        
        # Проверка наличия ключевых метрик
        if not metrics:
            recommendations.append({
                "recommendation": "Недостаточно данных для формирования рекомендаций",
                "confidence": "low",
                "reasoning": "Не удалось извлечь ключевые финансовые метрики из отчета."
            })
        else:
            # Анализ на основе упоминаний в тексте MD&A
            positive_indicators = ['growth', 'increase', 'higher', 'improve', 'expanded', 'success']
            negative_indicators = ['decline', 'decrease', 'lower', 'challenges', 'difficult', 'loss']
            
            positive_count = sum(1 for word in positive_indicators if re.search(r'\b' + word + r'\b', management_discussion, re.IGNORECASE))
            negative_count = sum(1 for word in negative_indicators if re.search(r'\b' + word + r'\b', management_discussion, re.IGNORECASE))
            
            # Анализ тона управления
            management_sentiment = "neutral"
            if positive_count > negative_count * 2:
                management_sentiment = "very positive"
            elif positive_count > negative_count:
                management_sentiment = "positive"
            elif negative_count > positive_count * 2:
                management_sentiment = "very negative"
            elif negative_count > positive_count:
                management_sentiment = "negative"
            
            # Анализ наличия выручки
            if "revenue" in metrics:
                recommendations.append({
                    "recommendation": "Обнаружены данные о выручке",
                    "confidence": "medium",
                    "reasoning": f"Выручка составляет {metrics['revenue']}. Для полного анализа требуется сравнение с предыдущими периодами."
                })
            
            # Анализ наличия EPS
            if "eps" in metrics:
                recommendations.append({
                    "recommendation": "Обнаружены данные о прибыли на акцию (EPS)",
                    "confidence": "medium",
                    "reasoning": f"EPS составляет {metrics['eps']}. Для полного анализа требуется сравнение с предыдущими периодами и ожиданиями аналитиков."
                })
            
            # Анализ тона руководства
            recommendations.append({
                "recommendation": f"Тон руководства в описании результатов: {management_sentiment}",
                "confidence": "medium",
                "reasoning": f"В разделе MD&A обнаружено {positive_count} позитивных и {negative_count} негативных индикаторов. Это может указывать на {management_sentiment} оценку руководством текущего положения компании."
            })
            
            # Анализ факторов риска
            if risk_factors:
                risk_count = len(re.findall(r'\.\s+', risk_factors))  # Примерное количество предложений
                
                if risk_count > 20:
                    recommendations.append({
                        "recommendation": "Компания сообщает о значительном количестве факторов риска",
                        "confidence": "medium",
                        "reasoning": f"Раздел Risk Factors содержит примерно {risk_count} пунктов, что может указывать на сложную операционную среду."
                    })
        
        return json.dumps({
            "company_name": company_name,
            "report_type": report_type,
            "period": period,
            "metrics": metrics,
            "sections_found": list(financial_sections.keys()),
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error analyzing report: {str(e)}")
        return json.dumps({
            "error": f"Error analyzing report: {str(e)}"
        })

@register_tool
def extract_specific_section(pdf_path: str, section_name: str) -> str:
    """
    Извлекает конкретный раздел из финансового отчета.
    
    Args:
        pdf_path: Путь к PDF-файлу
        section_name: Название раздела для извлечения (например, 'assets', 'liabilities', 'cash_flow')
        
    Returns:
        JSON строка с информацией о разделе и найденными данными
    """
    try:
        # Обработка путей формата "sandbox:..."
        clean_path = pdf_path
        if pdf_path.startswith("sandbox:"):
            clean_path = pdf_path[9:]  # Удаляем префикс "sandbox:"
        
        # Проверяем существование файла
        if not os.path.exists(clean_path):
            return json.dumps({
                "error": f"File not found: {clean_path}",
                "section": section_name,
                "content": ""
            })
        
        # Извлекаем текст из PDF
        text_result = json.loads(extract_text_from_pdf(pdf_path))
        
        if "error" in text_result:
            return json.dumps({
                "error": text_result["error"],
                "section": section_name,
                "content": ""
            })
            
        text = text_result.get("text", "")
        if not text:
            return json.dumps({
                "error": "No text extracted from PDF",
                "section": section_name,
                "content": ""
            })
        
        # Расширенный словарь ключевых слов для поиска различных разделов
        section_patterns = {
            "assets": [
                r"(?:total|current)\s+assets",
                r"assets\s+section",
                r"consolidated\s+balance\s+sheets?.*?assets",
                r"statement\s+of\s+financial\s+position.*?assets",
                r"balance\s+sheets?.*?assets",
            ],
            "liabilities": [
                r"(?:total|current)\s+liabilities",
                r"liabilities\s+section",
                r"consolidated\s+balance\s+sheets?.*?liabilities",
                r"statement\s+of\s+financial\s+position.*?liabilities",
                r"balance\s+sheets?.*?liabilities",
            ],
            "equity": [
                r"(?:stockholders'?|shareholders'?)\s+equity",
                r"equity\s+section",
                r"total\s+equity",
                r"(?:stockholders'?|shareholders'?)\s+(?:equity|investment)",
            ],
            "revenue": [
                r"(?:total\s+)?revenue[s]?",
                r"net\s+revenue[s]?",
                r"sales\s+revenue",
                r"consolidated\s+statements?\s+of\s+(?:income|operations|earnings).*?revenue",
            ],
            "income": [
                r"net\s+income",
                r"operating\s+income",
                r"income\s+(?:before|after)\s+tax(?:es)?",
                r"consolidated\s+statements?\s+of\s+(?:income|operations|earnings)",
                r"statements?\s+of\s+comprehensive\s+income",
            ],
            "cash_flow": [
                r"cash\s+flow[s]?",
                r"cash\s+and\s+cash\s+equivalents",
                r"operating\s+activities",
                r"consolidated\s+statements?\s+of\s+cash\s+flows?",
                r"statements?\s+of\s+cash\s+flows?",
            ],
            "balance_sheet": [
                r"consolidated\s+balance\s+sheets?",
                r"balance\s+sheets?",
                r"statement\s+of\s+financial\s+position",
            ],
            "income_statement": [
                r"consolidated\s+statements?\s+of\s+(?:income|operations|earnings)",
                r"statements?\s+of\s+(?:income|operations|earnings)",
                r"statements?\s+of\s+comprehensive\s+income",
            ],
        }
        
        # Если секция не определена в словаре или это пользовательский запрос, используем его как паттерн
        patterns = section_patterns.get(section_name.lower(), [section_name])
        
        # Ищем раздел
        section_content = ""
        
        # Сначала ищем явные заголовки разделов
        for pattern in patterns:
            # Ищем с контекстом - ограничим до 5000 символов чтобы избежать переполнения
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            if matches:
                for match in matches:
                    start_idx = match.start()
                    # Берем меньший фрагмент текста, чтобы избежать проблем с памятью
                    chunk = text[start_idx:start_idx + 5000]
                    section_content += chunk + "\n\n"
                    # Берем только первое совпадение для уменьшения объема данных
                    break
                # Если нашли хотя бы одно совпадение, прекращаем поиск
                if section_content:
                    break
        
        if not section_content:
            # Если не нашли по явным заголовкам, используем ключевые слова раздела
            related_keywords = json.loads(extract_related_keywords(section_name))
            
            for word in related_keywords[:5]:  # Берем только первые 5 ключевых слов
                word_matches = list(re.finditer(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE))
                if word_matches:
                    # Берем только первое совпадение
                    match = word_matches[0]
                    # Берем меньший контекст вокруг слова
                    start_pos = max(0, match.start() - 1000)
                    end_pos = min(len(text), match.end() + 1000)
                    chunk = text[start_pos:end_pos]
                    section_content += chunk + "\n\n"
                    break
                    
        if not section_content:
            return json.dumps({
                "error": f"Section {section_name} not found in the document",
                "section": section_name,
                "content": ""
            })
        
        # Извлекаем числовые данные, но ограничиваем их количество
        numerical_data = extract_numerical_data_enhanced(section_content)[:30]  # Ограничиваем до 30 значений
        
        # Создаем структурированный анализ раздела
        analysis = analyze_section_content(section_name, section_content, numerical_data)
        
        return json.dumps({
            "section": section_name,
            "content": section_content[:1500] + "..." if len(section_content) > 1500 else section_content,  # Сильно ограничиваем размер контента
            "numerical_data": numerical_data,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Error in extract_specific_section: {str(e)}")
        return json.dumps({
            "error": str(e),
            "section": section_name,
            "content": ""
        })

@register_tool
def extract_related_keywords(section_name: str) -> str:
    """
    Возвращает связанные ключевые слова для заданного раздела финансового отчета.
    
    Args:
        section_name: Название раздела
        
    Returns:
        JSON строка со списком связанных ключевых слов
    """
    # Словарь связанных терминов для различных разделов
    related_terms = {
        "assets": [
            "assets", "total assets", "current assets", "non-current assets",
            "cash", "cash equivalents", "accounts receivable", "inventory",
            "property", "equipment", "investments", "goodwill", "intangible"
        ],
        "liabilities": [
            "liabilities", "total liabilities", "current liabilities", "long-term liabilities",
            "accounts payable", "debt", "loans", "borrowings", "obligations", "accrued"
        ],
        "equity": [
            "equity", "stockholders' equity", "shareholders' equity", "common stock",
            "retained earnings", "treasury stock", "additional paid-in capital"
        ],
        "revenue": [
            "revenue", "net revenue", "gross revenue", "sales", "total revenue",
            "service revenue", "product revenue"
        ],
        "income": [
            "income", "net income", "profit", "earnings", "ebitda",
            "operating income", "income before tax", "comprehensive income"
        ],
        "cash_flow": [
            "cash flow", "operating activities", "investing activities", "financing activities",
            "cash provided by", "cash used in", "net cash", "cash and cash equivalents"
        ],
        "balance_sheet": [
            "balance sheet", "consolidated balance sheets", "statement of financial position",
            "assets", "liabilities", "equity", "current", "non-current"
        ],
        "income_statement": [
            "income statement", "statement of operations", "statement of earnings",
            "revenue", "expenses", "costs", "income", "earnings per share", "eps"
        ]
    }
    
    # Возвращает список ключевых слов для заданного раздела или общий список
    keywords = related_terms.get(section_name.lower(), ["financial", "balance", "income", "cash", "statement", "total", "net"])
    return json.dumps(keywords)

@register_tool
def summarize_report(analysis_result: str) -> str:
    """
    Создает текстовое резюме анализа отчета.
    
    Args:
        analysis_result: JSON строка с результатами анализа отчета
        
    Returns:
        Текстовое резюме
    """
    try:
        if isinstance(analysis_result, str):
            analysis_data = json.loads(analysis_result)
        else:
            analysis_data = analysis_result
    except json.JSONDecodeError:
        return "Ошибка анализа отчета: некорректный формат JSON"
    
    if "error" in analysis_data:
        return f"Ошибка анализа отчета: {analysis_data['error']}"
    
    summary = []
    summary.append(f"# Анализ финансового отчета {analysis_data.get('company_name', 'Компании')}")
    summary.append(f"## Тип отчета: {analysis_data.get('report_type', 'Неизвестный')}")
    summary.append(f"## Период: {analysis_data.get('period', 'Неизвестный')}")
    summary.append("")
    
    # Добавляем метрики
    summary.append("## Ключевые метрики:")
    if analysis_data.get('metrics'):
        for metric, value in analysis_data['metrics'].items():
            summary.append(f"- {metric.capitalize()}: {value}")
    else:
        summary.append("- Не удалось извлечь ключевые метрики")
    summary.append("")
    
    # Добавляем рекомендации
    summary.append("## Рекомендации и выводы:")
    if analysis_data.get('recommendations'):
        for rec in analysis_data['recommendations']:
            summary.append(f"- {rec['recommendation']}")
            if 'reasoning' in rec:
                summary.append(f"  Обоснование: {rec['reasoning']}")
            summary.append("")
    else:
        summary.append("- Не удалось сформировать рекомендации")
    
    summary.append("## Примечание:")
    summary.append("Данный анализ основан на автоматическом извлечении данных из отчета и является предварительным. Для принятия инвестиционных решений рекомендуется провести более глубокий анализ и проконсультироваться с финансовым консультантом.")
    
    return "\n".join(summary)

@register_tool
def get_and_analyze_latest_report(ticker: str, report_type: str) -> str:
    """
    Download the latest report for a company and analyze it in one step.
    
    Args:
        ticker: The stock ticker symbol of the company (e.g., 'AAPL' for Apple Inc.)
        report_type: Type of report to retrieve ('10-K' for annual or '10-Q' for quarterly)
        
    Returns:
        JSON строка с результатами анализа
    """
    try:
        # Проверяем тип отчета
        actual_report_type = report_type
        if report_type not in ["10-K", "10-Q"]:
            actual_report_type = "10-Q"
            
        # Скачиваем последний отчет
        from tools.sec_downloader import download_recent_filing_as_pdf
        download_result = json.loads(download_recent_filing_as_pdf(ticker, actual_report_type))
        
        if "error" in download_result:
            return json.dumps({
                "error": download_result["error"],
                "analysis": {}
            })
        
        file_path = download_result.get("file_path")
        if not file_path:
            return json.dumps({
                "error": "Failed to download report - no file path returned",
                "analysis": {}
            })
        
        # Анализируем скачанный отчет
        analysis_result = analyze_financial_report(file_path)
        analysis_data = json.loads(analysis_result)
        
        if "error" in analysis_data:
            return json.dumps({
                "error": analysis_data["error"],
                "file_path": file_path,
                "analysis": {}
            })
        
        # Создаем текстовое резюме для удобства
        summary = summarize_report(analysis_result)
        
        # Объединяем результаты
        result = {
            "result": f"Successfully downloaded and analyzed {actual_report_type} report for {ticker}",
            "ticker": ticker,
            "report_type": actual_report_type,
            "file_path": file_path,
            "company_name": analysis_data.get("company_name", "Unknown"),
            "report_type_detected": analysis_data.get("report_type", "Unknown"),
            "period": analysis_data.get("period", "Unknown"),
            "metrics": analysis_data.get("metrics", {}),
            "recommendations": analysis_data.get("recommendations", []),
            "summary": summary
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error in get_and_analyze_latest_report: {str(e)}")
        return json.dumps({"error": str(e)})