"""
Test script for SEC EDGAR API functions.
"""

import json
import sys
from tools.edgar_tools import (
    get_company_cik,
    get_company_filings,
    get_company_facts,
    get_recent_filings_summary,
    extract_financial_data
)

def print_json(data):
    """Print JSON data with indentation."""
    print(json.dumps(data, indent=2))

def test_get_company_cik(ticker):
    """Test the get_company_cik function."""
    print(f"\n=== Testing get_company_cik for {ticker} ===")
    cik = get_company_cik(ticker)
    print(f"CIK for {ticker}: {cik}")
    return cik

def test_get_company_filings(cik, limit=5):
    """Test the get_company_filings function."""
    print(f"\n=== Testing get_company_filings for CIK {cik} ===")
    filings = get_company_filings(cik, limit=limit)
    print("Company filings:")
    print_json(filings)
    return filings

def test_get_company_facts(cik):
    """Test the get_company_facts function."""
    print(f"\n=== Testing get_company_facts for CIK {cik} ===")
    facts = get_company_facts(cik)
    if "error" in facts:
        print(f"Error: {facts['error']}")
    else:
        print(f"Company name: {facts.get('entityName', 'Unknown')}")
        print(f"Number of fact categories: {len(facts.get('facts', {}))}")
    return facts

def test_extract_financial_data(cik, concept="Revenue"):
    """Test the extract_financial_data function."""
    print(f"\n=== Testing extract_financial_data for CIK {cik}, concept: {concept} ===")
    data = extract_financial_data(cik, concept)
    print("Financial data:")
    print_json(data)
    return data

def test_get_recent_filings_summary(ticker, limit=5):
    """Test the get_recent_filings_summary function."""
    print(f"\n=== Testing get_recent_filings_summary for {ticker} ===")
    summary = get_recent_filings_summary(ticker, limit=limit)
    print("Filings summary:")
    print_json(summary)
    return summary

def main():
    """Main function to run tests."""
    # Check if a ticker was passed as a command-line argument
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    else:
        ticker = "AAPL"  # Default to Apple if no ticker provided
    
    print(f"Testing SEC EDGAR API functions for {ticker}")
    
    # Test get_company_cik
    cik = test_get_company_cik(ticker)
    if not cik:
        print(f"Could not find CIK for {ticker}. Exiting.")
        return
    
    # Test get_company_filings
    test_get_company_filings(cik)
    
    # Test get_company_facts
    test_get_company_facts(cik)
    
    # Test extract_financial_data
    test_extract_financial_data(cik)
    
    # Test get_recent_filings_summary
    test_get_recent_filings_summary(ticker)

if __name__ == "__main__":
    main()