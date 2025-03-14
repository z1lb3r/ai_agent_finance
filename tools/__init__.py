"""
Initialize the tools package and export main functions.
"""

# Импортируем и экспортируем функции из sec_downloader
try:
    from tools.sec_downloader import (
        search_filings,
        download_filing_as_pdf,
        get_recent_filing,
        download_recent_filing_as_pdf,
        search_filings_by_period,
        format_filing_summary,
        get_filing_list_summary
    )
except ImportError:
    pass

# Импортируем и экспортируем функции из pdf_analyzer
try:
    from tools.pdf_analyzer import (
        extract_text_from_pdf,
        extract_tables_from_pdf,
        find_financial_tables,
        extract_key_metrics,
        analyze_financial_report,
        generate_recommendations,
        summarize_report,
        extract_specific_section,
        extract_related_keywords,
        extract_numerical_data_enhanced,
        analyze_section_content
    )
except ImportError:
    pass

# Определяем, какие функции будут доступны при импорте из пакета
__all__ = [
    # Функции из sec_downloader
    'search_filings',
    'download_filing_as_pdf',
    'get_recent_filing',
    'download_recent_filing_as_pdf',
    'search_filings_by_period',
    'format_filing_summary',
    'get_filing_list_summary',
    
    # Функции из pdf_analyzer
    'extract_text_from_pdf',
    'extract_tables_from_pdf',
    'find_financial_tables',
    'extract_key_metrics',
    'analyze_financial_report',
    'generate_recommendations',
    'summarize_report',
    'extract_specific_section',
    'extract_related_keywords',
    'extract_numerical_data_enhanced',
    'analyze_section_content'
]