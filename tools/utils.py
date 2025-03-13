"""
Utility functions for the Investment AI Agent.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Simple in-memory cache
_cache = {}

def cache_result(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    """
    Cache a result with an expiration time.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time-to-live in seconds
    """
    expiry = time.time() + ttl_seconds
    _cache[key] = (value, expiry)

def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a cached result if it exists and hasn't expired.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found or expired
    """
    if key in _cache:
        value, expiry = _cache[key]
        if time.time() < expiry:
            return value
        else:
            # Clean up expired entry
            del _cache[key]
    return None

def clear_cache() -> None:
    """Clear the entire cache."""
    global _cache
    _cache = {}

def clean_expired_cache() -> None:
    """Remove expired entries from the cache."""
    current_time = time.time()
    keys_to_delete = [
        key for key, (_, expiry) in _cache.items() 
        if current_time >= expiry
    ]
    for key in keys_to_delete:
        del _cache[key]

def format_currency(value: float, currency: str = "USD") -> str:
    """
    Format a number as currency.
    
    Args:
        value: The value to format
        currency: Currency code (default: "USD")
        
    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${value:,.2f}"
    return f"{value:,.2f} {currency}"

def calculate_growth_rate(current_value: float, previous_value: float) -> float:
    """
    Calculate growth rate between two values.
    
    Args:
        current_value: Current value
        previous_value: Previous value
        
    Returns:
        Growth rate as a percentage
    """
    if previous_value == 0:
        return float('inf') if current_value > 0 else float('-inf') if current_value < 0 else 0
    
    return ((current_value - previous_value) / abs(previous_value)) * 100

def extract_latest_value(data: Dict) -> Optional[Dict]:
    """
    Extract the latest value from a financial data structure.
    Typically used for SEC EDGAR API responses.
    
    Args:
        data: Financial data dictionary
        
    Returns:
        Latest value with associated metadata, or None if not available
    """
    if not data or "units" not in data:
        return None
    
    for unit_type, values in data["units"].items():
        # Sort values by end date in descending order
        sorted_values = sorted(
            values, 
            key=lambda x: x.get("end", "0000-00-00"), 
            reverse=True
        )
        
        if sorted_values:
            latest = sorted_values[0]
            return {
                "value": latest.get("val", None),
                "unit": unit_type,
                "end_date": latest.get("end", None),
                "start_date": latest.get("start", None),
                "filed_date": latest.get("filed", None),
                "form": latest.get("form", None)
            }
    
    return None

def summarize_financial_data(data: Dict, num_periods: int = 5) -> Dict:
    """
    Summarize financial data to show trends over time.
    
    Args:
        data: Financial data dictionary
        num_periods: Number of time periods to include
        
    Returns:
        Dictionary with summarized financial data
    """
    if not data or "units" not in data:
        return {"error": "Invalid data format"}
    
    result = {}
    
    for unit_type, values in data["units"].items():
        # Sort values by end date in descending order
        sorted_values = sorted(
            values, 
            key=lambda x: x.get("end", "0000-00-00"), 
            reverse=True
        )
        
        # Take only the specified number of periods
        selected_values = sorted_values[:num_periods]
        
        # Reverse to get chronological order
        selected_values.reverse()
        
        result[unit_type] = [
            {
                "value": item.get("val", None),
                "end_date": item.get("end", None),
                "form": item.get("form", None)
            }
            for item in selected_values
        ]
    
    return result