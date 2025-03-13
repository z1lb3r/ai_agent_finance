"""
Initialize the tools package and export all tools.
"""

from tools.edgar_tools import (
    get_company_cik,
    get_company_filings,
    get_company_facts,
    get_filing_text,
    extract_financial_data
)

from tools.market_analysis import (
    get_market_summary,
    get_sector_performance,
    get_economic_indicators,
    get_market_news
)

from tools.company_tools import (
    get_company_profile,
    get_financial_metrics,
    get_recent_filings_summary,
    compare_companies
)

from tools.utils import (
    cache_result,
    get_cached_result,
    clear_cache,
    clean_expired_cache,
    format_currency,
    calculate_growth_rate,
    extract_latest_value,
    summarize_financial_data
)

# Export all tools
__all__ = [
    # Edgar tools
    'get_company_cik',
    'get_company_filings',
    'get_company_facts',
    'get_filing_text',
    'extract_financial_data',
    
    # Market analysis tools
    'get_market_summary',
    'get_sector_performance',
    'get_economic_indicators',
    'get_market_news',
    
    # Company tools
    'get_company_profile',
    'get_financial_metrics',
    'get_recent_filings_summary',
    'compare_companies',
    
    # Utility functions
    'cache_result',
    'get_cached_result',
    'clear_cache',
    'clean_expired_cache',
    'format_currency',
    'calculate_growth_rate',
    'extract_latest_value',
    'summarize_financial_data'
]