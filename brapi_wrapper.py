import requests
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from typing import Union, List, Dict, Optional
from tools import (
    get_quote_list,
    get_quote,
    get_balance_sheet_history,
    get_income_statements,
    get_financial_data,
    get_default_key_statistics,
    get_inflation,
    get_prime_rate
)

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_balance_sheet_data(ticker: str) -> Optional[Dict]:
    """Get balance sheet data for a Brazilian stock."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            raise ValueError("BRAPI_TOKEN not found in environment variables")

        url = f"{BASE_URL}/fundamental/balance_sheet"
        params = {
            'token': API_KEY,
            'ticker': ticker,
            'interval': 'yearly'
        }

        annual_data = None
        quarterly_data = None

        # Get annual data
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                annual_data = data['results']

        # Get quarterly data
        params['interval'] = 'quarterly'
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                quarterly_data = data['results']

        if not annual_data and not quarterly_data:
            logger.error("No balance sheet statements found in response")
            return None

        return {
            'annual': annual_data,
            'quarterly': quarterly_data
        }

    except Exception as e:
        logger.error(f"Error getting balance sheet data: {str(e)}")
        return None

