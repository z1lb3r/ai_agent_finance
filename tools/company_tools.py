"""
Tools for company-specific analysis and information retrieval.
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Union

from config import REQUEST_TIMEOUT
from tools.edgar_tools import get_company_cik, get_company_filings, get_company_facts, extract_financial_data

def get_company_profile(ticker: str) -> Dict:
    """
    Get a comprehensive profile of a company.
    
    Args:
        ticker: The stock ticker symbol of the company
        
    Returns:
        Dictionary containing company profile information
    """
    try:
        # Get CIK from ticker
        cik = get_company_cik(ticker)
        if not cik:
            return {"error": f"Could not find CIK for ticker {ticker}"}
        
        # Get basic company information
        filings_data = get_company_filings(cik, limit=1)
        company_name = filings_data.get("company", "Unknown")
        
        # Get company facts
        facts = get_company_facts(cik)
        
        # This would be enhanced with additional data sources in a production environment
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "name": company_name,
            "profile_data": {
                "source": "SEC EDGAR",
                "retrieved_at": datetime.now().isoformat(),
                "basic_info": filings_data.get("filings", []),
                "facts": facts
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_financial_metrics(ticker: str) -> Dict:
    """
    Get key financial metrics for a company.
    
    Args:
        ticker: The stock ticker symbol of the company
        
    Returns:
        Dictionary containing financial metrics
    """
    try:
        # Get CIK from ticker
        cik = get_company_cik(ticker)
        if not cik:
            return {"error": f"Could not find CIK for ticker {ticker}"}
        
        # Extract key financial metrics
        # These concepts may need adjustment based on actual availability in SEC data
        revenue = extract_financial_data(cik, "Revenue")
        assets = extract_financial_data(cik, "Assets")
        liabilities = extract_financial_data(cik, "Liabilities")
        net_income = extract_financial_data(cik, "NetIncomeLoss")
        
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "metrics": {
                "source": "SEC EDGAR",
                "retrieved_at": datetime.now().isoformat(),
                "revenue": revenue.get("data", {}),
                "assets": assets.get("data", {}),
                "liabilities": liabilities.get("data", {}),
                "net_income": net_income.get("data", {})
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_recent_filings_summary(ticker: str, limit: int = 5) -> Dict:
    """
    Get a summary of recent SEC filings for a company.
    
    Args:
        ticker: The stock ticker symbol of the company
        limit: Maximum number of filings to retrieve
        
    Returns:
        Dictionary containing summaries of recent filings
    """
    try:
        # Get CIK from ticker
        cik = get_company_cik(ticker)
        if not cik:
            return {"error": f"Could not find CIK for ticker {ticker}"}
        
        # Get recent filings
        filings_data = get_company_filings(cik, limit=limit)
        
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "company_name": filings_data.get("company", "Unknown"),
            "filings": filings_data.get("filings", []),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

def compare_companies(tickers: List[str], metrics: List[str] = None) -> Dict:
    """
    Compare multiple companies across specified metrics.
    
    Args:
        tickers: List of stock ticker symbols
        metrics: List of metrics to compare (if None, uses a default set)
        
    Returns:
        Dictionary containing comparison data
    """
    if metrics is None:
        metrics = ["Revenue", "Assets", "Liabilities", "NetIncomeLoss"]
    
    comparison = {}
    companies = []
    
    for ticker in tickers:
        cik = get_company_cik(ticker)
        if not cik:
            companies.append({
                "ticker": ticker.upper(),
                "error": f"Could not find CIK for ticker {ticker}"
            })
            continue
        
        filings_data = get_company_filings(cik, limit=1)
        company_name = filings_data.get("company", "Unknown")
        
        company_metrics = {}
        for metric in metrics:
            data = extract_financial_data(cik, metric)
            company_metrics[metric] = data.get("data", {})
        
        companies.append({
            "ticker": ticker.upper(),
            "cik": cik,
            "name": company_name,
            "metrics": company_metrics
        })
    
    comparison = {
        "tickers": tickers,
        "metrics": metrics,
        "companies": companies,
        "retrieved_at": datetime.now().isoformat()
    }
    
    return comparison   