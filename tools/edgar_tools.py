"""
Tools for interacting with the SEC EDGAR database to retrieve financial information.
"""

import requests
import json
from datetime import datetime
import time
from typing import Dict, List, Optional, Tuple, Union

from config import SEC_EDGAR_USER_AGENT, REQUEST_TIMEOUT

# Base URLs for SEC EDGAR API
EDGAR_BASE_URL = "https://www.sec.gov/edgar"
EDGAR_DATA_BASE_URL = "https://data.sec.gov"
EDGAR_COMPANY_FACTS_URL = f"{EDGAR_DATA_BASE_URL}/api/xbrl/companyfacts"
EDGAR_COMPANY_CONCEPT_URL = f"{EDGAR_DATA_BASE_URL}/api/xbrl/companyconcept"
EDGAR_SUBMISSION_URL = f"{EDGAR_DATA_BASE_URL}/submissions"
EDGAR_SEARCH_URL = f"{EDGAR_BASE_URL}/search-and-access/api/document"

# Headers for SEC EDGAR API requests
EDGAR_HEADERS = {
    "User-Agent": SEC_EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}

def get_company_cik(ticker: str) -> Optional[str]:
    """
    Get the CIK (Central Index Key) for a company based on its ticker symbol.
    
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL' for Apple Inc.)
        
    Returns:
        The CIK number as a string, or None if not found
    """
    try:
        url = f"https://www.sec.gov/files/company_tickers.json"
        
        # Для запроса к www.sec.gov используем другой хост в заголовках
        headers = {
            "User-Agent": SEC_EDGAR_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
        
        print(f"Requesting company tickers from: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        companies = response.json()
        
        # Convert ticker to uppercase for case-insensitive matching
        ticker = ticker.upper()
        
        # Search for the company
        for _, company in companies.items():
            if company['ticker'] == ticker:
                # Format CIK with leading zeros to 10 digits
                cik = str(company['cik_str']).zfill(10)
                print(f"Found CIK for {ticker}: {cik}")
                return cik
        
        print(f"CIK not found for ticker: {ticker}")
        return None
    
    except Exception as e:
        print(f"Error retrieving CIK for {ticker}: {e}")
        return None

def get_company_filings(cik: str, filing_type: str = None, limit: int = 10) -> Dict:
    """
    Get recent SEC filings for a company.
    
    Args:
        cik: The CIK number of the company
        filing_type: The type of filing to retrieve (e.g., '10-K', '10-Q')
        limit: Maximum number of filings to retrieve
        
    Returns:
        Dictionary containing filing information
    """
    try:
        # Ensure CIK is formatted correctly - must be exactly 10 digits with leading zeros
        cik = str(cik).strip().zfill(10)
        
        # Используем правильный URL формат в соответствии с документацией SEC EDGAR API
        url = f"{EDGAR_SUBMISSION_URL}/CIK{cik}.json"
        
        print(f"Requesting company filings from: {url}")
        response = requests.get(url, headers=EDGAR_HEADERS, timeout=REQUEST_TIMEOUT)
        
        # Проверим ответ перед вызовом raise_for_status
        if response.status_code != 200:
            print(f"Error status code: {response.status_code}, URL: {url}")
            print(f"Response text: {response.text[:200]}...")  # Print the first 200 chars of response
            
        response.raise_for_status()
        
        data = response.json()
        filings = data.get("filings", {}).get("recent", {})
        
        # Filter by filing type if specified
        if filing_type and "form" in filings:
            filtered_filings = []
            for i, form in enumerate(filings["form"]):
                if form == filing_type and i < limit:
                    filing_data = {}
                    for key in filings.keys():
                        if i < len(filings[key]):
                            filing_data[key] = filings[key][i]
                    filtered_filings.append(filing_data)
            return {"filings": filtered_filings, "company": data.get("name", "")}
        
        # Otherwise, return all filings up to the limit
        result_filings = []
        filing_count = min(limit, len(filings.get("form", [])))
        
        for i in range(filing_count):
            filing_data = {}
            for key in filings.keys():
                if i < len(filings[key]):
                    filing_data[key] = filings[key][i]
            result_filings.append(filing_data)
        
        return {"filings": result_filings, "company": data.get("name", "")}
    
    except Exception as e:
        print(f"Error retrieving filings for CIK {cik}: {e}")
        return {"filings": [], "company": "", "error": str(e)}

def get_company_facts(cik: str) -> Dict:
    """
    Get key financial facts about a company from SEC EDGAR.
    
    Args:
        cik: The CIK number of the company
        
    Returns:
        Dictionary containing key financial facts
    """
    try:
        # Ensure CIK is formatted correctly with 10 digits including leading zeros
        cik = str(cik).strip().zfill(10)
        
        url = f"{EDGAR_COMPANY_FACTS_URL}/CIK{cik}.json"
        print(f"Requesting company facts from: {url}")
        response = requests.get(url, headers=EDGAR_HEADERS, timeout=REQUEST_TIMEOUT)
        
        # Проверим ответ перед вызовом raise_for_status
        if response.status_code != 200:
            print(f"Error status code: {response.status_code}, URL: {url}")
            print(f"Response text: {response.text[:200]}...")  # Print the first 200 chars of response
            
        response.raise_for_status()
        
        return response.json()
    
    except Exception as e:
        print(f"Error retrieving company facts for CIK {cik}: {e}")
        return {"error": str(e)}

def get_filing_text(accession_number: str, cik: str) -> str:
    """
    Get the text content of a specific SEC filing.
    
    Args:
        accession_number: The accession number of the filing
        cik: The CIK number of the company
        
    Returns:
        Text content of the filing
    """
    try:
        # Format CIK and accession number
        cik = str(cik).strip().zfill(10)
        accession_number = accession_number.replace("-", "")
        
        # Для запроса к www.sec.gov используем другой хост в заголовках
        headers = {
            "User-Agent": SEC_EDGAR_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
        
        url = f"{EDGAR_SEARCH_URL}/api/fetch?accession={accession_number}"
        print(f"Requesting filing text from: {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        # Проверим ответ перед вызовом raise_for_status
        if response.status_code != 200:
            print(f"Error status code: {response.status_code}, URL: {url}")
            print(f"Response text: {response.text[:200]}...")  # Print the first 200 chars of response
            
        response.raise_for_status()
        
        return response.text
    
    except Exception as e:
        print(f"Error retrieving filing text for accession {accession_number}: {e}")
        return f"Error: {str(e)}"

def extract_financial_data(cik: str, concept: str, taxonomy: str = "us-gaap") -> Dict:
    """
    Extract specific financial data points for a company.
    
    Args:
        cik: The CIK number of the company
        concept: The financial concept to extract (e.g., 'Revenue', 'Assets')
        taxonomy: The taxonomy to use (default: 'us-gaap')
        
    Returns:
        Dictionary containing the financial data
    """
    try:
        # Ensure CIK is formatted correctly with 10 digits including leading zeros
        cik = str(cik).strip().zfill(10)
        
        url = f"{EDGAR_COMPANY_CONCEPT_URL}/CIK{cik}/{taxonomy}/{concept}.json"
        print(f"Requesting financial data from: {url}")
        response = requests.get(url, headers=EDGAR_HEADERS, timeout=REQUEST_TIMEOUT)
        
        # Проверим ответ перед вызовом raise_for_status
        if response.status_code != 200:
            print(f"Error status code: {response.status_code}, URL: {url}")
            print(f"Response text: {response.text[:200]}...")  # Print the first 200 chars of response
            
            # Если концепт не найден, вернем соответствующее сообщение
            if response.status_code == 404:
                return {
                    "company": "Unknown",
                    "cik": cik,
                    "concept": concept,
                    "error": f"Financial concept '{concept}' not found for this company"
                }
            
        response.raise_for_status()
        data = response.json()
        
        company_name = data.get("entityName", "")
        
        return {
            "company": company_name,
            "cik": cik,
            "concept": concept,
            "data": data
        }
    
    except Exception as e:
        print(f"Error extracting {concept} data for CIK {cik}: {e}")
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
        
        print(f"Getting filings for {ticker} (CIK: {cik})")
        
        # Get recent filings
        filings_data = get_company_filings(cik, limit=limit)
        
        # Проверяем, есть ли в ответе ошибка
        if "error" in filings_data:
            print(f"Error in filings data: {filings_data['error']}")
            return {
                "ticker": ticker.upper(),
                "cik": cik,
                "error": filings_data.get("error", "Unknown error"),
                "retrieved_at": datetime.now().isoformat()
            }
        
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "company_name": filings_data.get("company", "Unknown"),
            "filings": filings_data.get("filings", []),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Exception in get_recent_filings_summary: {e}")
        return {"error": str(e)}