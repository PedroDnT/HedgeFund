from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import os
import requests
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class GetIncomeStatementsInput(BaseModel):
    """Input model for fetching company income statements from Brapi API"""
    tickers: Union[str, List[str]] = Field(
        ..., 
        description="Stock ticker(s) from B3 (e.g. 'PETR4' or ['PETR4', 'VALE3'])"
    )
    range: str = Field(
        default='5y',
        description="Time range for historical data"
    )

@tool
def get_income_statements(tickers: Union[str, List[str]], range: str = '5y') -> Optional[Dict]:
    """Get income statements for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'range': range,
            'fundamental': 'true',
            'modules': 'incomeStatementHistory'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # Filter data to only include relevant fields
            filtered_data = {symbol: {
                'incomeStatementHistory': result.get('incomeStatementHistory', {})
            } for symbol, result in data.get('results', {}).items()}
            return filtered_data
        
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching income statement: {str(e)}")
        return None

class GetQuoteListInput(BaseModel):
    """Input model for get_quote_list function"""
    search: Optional[str] = Field(
        default=None,
        description="Search term to filter quotes"
    )
    sort_by: Optional[str] = Field(
        default=None,
        description="Field to sort results by"
    )
    sort_order: str = Field(
        default='desc',
        description="Sort order ('asc' or 'desc')"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of results to return"
    )
    sector: Optional[str] = Field(
        default=None,
        description="Filter by sector"
    )

@tool
def get_quote_list(
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = 'desc',
    limit: Optional[int] = None,
    sector: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """Fetch list of quotes with filtering and sorting."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        url = f"{BASE_URL}/quote/list"
        params = {k: v for k, v in {
            'token': API_KEY,
            'search': search,
            'sortBy': sort_by,
            'sortOrder': sort_order,
            'limit': limit,
            'sector': sector
        }.items() if v is not None}
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    keys = set().union(*(d.keys() for d in data))
                    cleaned_data = [{k: d.get(k, None) for k in keys} for d in data]
                    return {'stocks': pd.DataFrame(cleaned_data)}
                else:
                    logger.error("Unexpected data format: Expected a list")
                    return {'stocks': pd.DataFrame()}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response text: {response.text[:500]}")
                return {'stocks': pd.DataFrame()}
        
        logger.error(f"Request failed with status code {response.status_code}")
        return {'stocks': pd.DataFrame()}
            
    except Exception as e:
        logger.error(f"Error fetching quote list: {str(e)}")
        return {'stocks': pd.DataFrame()}

class GetQuoteInput(BaseModel):
    """Input model for get_quote function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )
    range: str = Field(
        default='1d',
        description="Time range ('1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')"
    )
    interval: str = Field(
        default='1d',
        description="Time interval ('1m','2m','5m','15m','30m','60m','90m','1h','1d','5d','1wk','1mo','3mo')"
    )
    fundamental: bool = Field(
        default=False,
        description="Include fundamental data"
    )

@tool
def get_quote(
    tickers: Union[str, List[str]], 
    range: str = '1d',
    interval: str = '1d',
    fundamental: bool = False
) -> Optional[Dict]:
    """Get stock quotes and price history for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'range': range,
            'interval': interval,
            'fundamental': 'true' if fundamental else 'false'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        
        logger.error(f"Failed to fetch quote data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching quote data: {str(e)}")
        return None

class GetBalanceSheetHistoryInput(BaseModel):
    """Input model for get_balance_sheet_history function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )
    range: str = Field(
        default='5y',
        description="Time range ('1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')"
    )

@tool
def get_balance_sheet_history(
    tickers: Union[str, List[str]],
    range: str = '5y'
) -> Optional[Dict]:
    """Get balance sheets for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'range': range,
            'fundamental': 'true',
            'modules': 'balanceSheetHistory'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching balance sheet: {str(e)}")
        return None

class GetFinancialDataInput(BaseModel):
    """Input model for get_financial_data function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )

@tool
def get_financial_data(tickers: Union[str, List[str]]) -> Optional[Dict]:
    """Get key financial metrics for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'fundamental': 'true',
            'modules': 'financialData'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching financial data: {str(e)}")
        return None

class GetDefaultKeyStatisticsInput(BaseModel):
    """Input model for get_default_key_statistics function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )

@tool
def get_default_key_statistics(tickers: Union[str, List[str]]) -> Optional[Dict]:
    """Get key statistics for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'fundamental': 'true',
            'modules': 'defaultKeyStatistics'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching key statistics: {str(e)}")
        return None

class GetInflationInput(BaseModel):
    """Input model for get_inflation function"""
    historical: bool = Field(
        default=True,
        description="Whether to get historical data"
    )
    start: Optional[str] = Field(
        default=None,
        description="Start date in DD/MM/YYYY format"
    )
    end: Optional[str] = Field(
        default=None,
        description="End date in DD/MM/YYYY format"
    )

@tool
def get_inflation(
    historical: bool = True,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[Dict]:
    """Fetch Brazilian inflation data."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if start is None:
            two_years_ago = datetime.now() - timedelta(days=365*2)
            start = two_years_ago.strftime('%d/%m/%Y')
            
        if end is None:
            end = datetime.now().strftime('%d/%m/%Y')
        
        url = f"{BASE_URL}/v2/inflation"
        params = {
            'token': API_KEY,
            'country': 'brazil',
            'historical': 'true' if historical else 'false',
            'start': start,
            'end': end,
            'sortBy': 'date',
            'sortOrder': 'desc'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching inflation data: {str(e)}")
        return None

class GetPrimeRateInput(BaseModel):
    """Input model for get_prime_rate function"""
    historical: bool = Field(
        default=True,
        description="Whether to get historical data"
    )
    start: Optional[str] = Field(
        default=None,
        description="Start date in DD/MM/YYYY format"
    )
    end: Optional[str] = Field(
        default=None,
        description="End date in DD/MM/YYYY format"
    )

@tool
def get_prime_rate(
    historical: bool = True,
    start: Optional[str] = None,
    end: Optional[str] = None
) -> Optional[Dict]:
    """Fetch Brazilian prime rate (SELIC) data."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if start is None:
            two_years_ago = datetime.now() - timedelta(days=365*2)
            start = two_years_ago.strftime('%d/%m/%Y')
            
        if end is None:
            end = datetime.now().strftime('%d/%m/%Y')
        
        url = f"{BASE_URL}/v2/prime-rate"
        params = {
            'token': API_KEY,
            'country': 'brazil',
            'historical': 'true' if historical else 'false',
            'start': start,
            'end': end,
            'sortBy': 'date',
            'sortOrder': 'desc'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching prime rate data: {str(e)}")
        return None

# Add this class and function to tools.py
class GetIncomeStatementHistoryQuarterlyInput(BaseModel):
    """Input model for get_income_statement_history_quarterly function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )
    range: str = Field(
        default='5y',
        description="Time range ('1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')"
    )

@tool
def get_income_statement_history_quarterly(
    tickers: Union[str, List[str]],
    range: str = '5y'
) -> Optional[Dict]:
    """Fetch quarterly income statement history for multiple tickers."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'range': range,
            'fundamental': 'true',
            'modules': 'incomeStatementHistoryQuarterly'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching quarterly income statement: {str(e)}")
        return None

# Also add the quarterly balance sheet function that might be needed
class GetBalanceSheetHistoryQuarterlyInput(BaseModel):
    """Input model for get_balance_sheet_history_quarterly function"""
    tickers: Union[str, List[str]] = Field(
        ...,
        description="Single ticker or list of ticker symbols"
    )
    range: str = Field(
        default='5y',
        description="Time range ('1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')"
    )

@tool
def get_balance_sheet_history_quarterly(
    tickers: Union[str, List[str]],
    range: str = '5y'
) -> Optional[Dict]:
    """Fetch quarterly balance sheet history for multiple tickers."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            logger.error("BRAPI_TOKEN not found in environment variables")
            return None
            
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'range': range,
            'fundamental': 'true',
            'modules': 'balanceSheetHistoryQuarterly'
        }
        
        logger.debug(f"Making request to: {url}")
        logger.debug(f"With params (token hidden): {dict(params, token='HIDDEN')}")
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
            
        logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching quarterly balance sheet: {str(e)}")
        return None

# Rest of the code remains the same... 