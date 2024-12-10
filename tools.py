from typing import List, Dict, Optional, Union, Any
from pydantic import BaseModel, Field, model_validator
from langchain_core.tools import tool
import os
import requests
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Constants for BRAPI API
VALID_RANGES = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
VALID_INTERVALS = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']

# Module names from BRAPI API documentation
BRAPI_MODULES = {
    'summary_profile': 'summaryProfile',  # Company overview
    'balance_sheet': 'balanceSheetHistory',  # Annual balance sheets
    'balance_sheet_quarterly': 'balanceSheetHistoryQuarterly',  # Quarterly balance sheets
    'income_statement': 'incomeStatementHistory',  # Annual income statements
    'income_statement_quarterly': 'incomeStatementHistoryQuarterly',  # Quarterly income statements
    'financial_data': 'financialData',  # Current financial metrics
    'key_statistics': 'defaultKeyStatistics'  # Key company statistics
}

def get_module_list(*modules) -> str:
    """Convert module names to comma-separated list for API request"""
    return ','.join(BRAPI_MODULES[module] for module in modules)

# Base Models for API Responses
class IncomeStatementItem(BaseModel):
    """Income statement data structure"""
    endDate: str
    totalRevenue: Optional[float] = None
    costOfRevenue: Optional[float] = None
    grossProfit: Optional[float] = None
    operatingIncome: Optional[float] = None
    netIncome: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None

    class Config:
        extra = "allow"

class BalanceSheetItem(BaseModel):
    """Balance sheet data structure"""
    endDate: str
    cash: Optional[float] = None
    totalAssets: Optional[float] = None
    totalLiabilities: Optional[float] = None
    totalStockholderEquity: Optional[float] = None
    totalCurrentAssets: Optional[float] = None
    totalCurrentLiabilities: Optional[float] = None
    netTangibleAssets: Optional[float] = None

    class Config:
        extra = "allow"

class FinancialDataItem(BaseModel):
    """Financial metrics data structure"""
    currentPrice: Optional[float] = None
    targetHighPrice: Optional[float] = None
    targetLowPrice: Optional[float] = None
    targetMeanPrice: Optional[float] = None
    recommendationMean: Optional[float] = None
    recommendationKey: Optional[str] = None
    numberOfAnalystOpinions: Optional[int] = None
    totalCash: Optional[float] = None
    totalDebt: Optional[float] = None
    debtToEquity: Optional[float] = None
    returnOnEquity: Optional[float] = None
    freeCashflow: Optional[float] = None
    operatingCashflow: Optional[float] = None
    revenueGrowth: Optional[float] = None
    grossMargins: Optional[float] = None
    operatingMargins: Optional[float] = None
    profitMargins: Optional[float] = None

    class Config:
        extra = "allow"

class KeyStatistics(BaseModel):
    """Key statistics data structure"""
    priceHint: Optional[int] = None
    enterpriseValue: Optional[float] = None
    forwardPE: Optional[float] = None
    profitMargins: Optional[float] = None
    floatShares: Optional[float] = None
    sharesOutstanding: Optional[float] = None
    bookValue: Optional[float] = None
    priceToBook: Optional[float] = None
    earningsQuarterlyGrowth: Optional[float] = None
    netIncomeToCommon: Optional[float] = None
    trailingEps: Optional[float] = None
    forwardEps: Optional[float] = None
    pegRatio: Optional[float] = None

    class Config:
        extra = "allow"

class StockQuote(BaseModel):
    """Stock quote data structure"""
    symbol: str
    shortName: Optional[str] = None
    longName: Optional[str] = None
    currency: Optional[str] = None
    regularMarketPrice: Optional[float] = None
    regularMarketChange: Optional[float] = None
    regularMarketChangePercent: Optional[float] = None
    regularMarketVolume: Optional[int] = None
    marketCap: Optional[float] = None
    fiftyTwoWeekLow: Optional[float] = None
    fiftyTwoWeekHigh: Optional[float] = None
    averageDailyVolume3Month: Optional[int] = None

    class Config:
        extra = "allow"

class APIResponse(BaseModel):
    """Base API response structure"""
    results: Union[List[Dict[str, Any]], Dict[str, Any]]
    requestedAt: Optional[str] = Field(default=None, validate_default=True)
    took: Optional[str] = Field(default=None, validate_default=True)

    @model_validator(mode='before')
    @classmethod
    def validate_results(cls, values):
        if not isinstance(values, dict):
            return values
        results = values.get('results', [])
        if results is None:
            values['results'] = []
        elif isinstance(results, dict):
            values['results'] = [results]
        return values

def validate_range(range_value: str) -> str:
    """
    Validate and return the range parameter.
    Valid ranges:
    - 1d: One trading day, including current day
    - 5d: Five trading days, including current day
    - 1mo: One month of trading, including current day
    - 3mo: Three months of trading, including current day
    - 6mo: Six months of trading, including current day
    - 1y: One year of trading, including current day
    - 2y: Two years of trading, including current day
    - 5y: Five years of trading, including current day
    - 10y: Ten years of trading, including current day
    - ytd: Year to date
    - max: All available data
    """
    if range_value not in VALID_RANGES:
        logger.warning(f"Invalid range '{range_value}'. Using default '1mo'. Valid ranges: {VALID_RANGES}")
        return '1mo'  # Changed default from '1y' to '1mo' for better data availability
    return range_value

def validate_interval(interval: str) -> str:
    """
    Validate and return the interval parameter.
    Valid intervals:
    - 1m: One minute
    - 2m: Two minutes
    - 5m: Five minutes
    - 15m: Fifteen minutes
    - 30m: Thirty minutes
    - 60m: Sixty minutes
    - 90m: Ninety minutes
    - 1h: One hour
    - 1d: One day
    - 5d: Five days
    - 1wk: One week
    - 1mo: One month
    - 3mo: Three months
    """
    if interval not in VALID_INTERVALS:
        logger.warning(f"Invalid interval '{interval}'. Using default '1d'. Valid intervals: {VALID_INTERVALS}")
        return '1d'
    return interval

def handle_brapi_response(response: requests.Response, expected_module: str = None) -> Optional[Dict]:
    """Common handler for BRAPI API responses"""
    try:
        if response.status_code == 400:
            error_data = response.json()
            if 'message' in error_data:
                logger.error(f"API request failed: {error_data['message']}")
                return None
        elif response.status_code != 200:
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            return None

        data = response.json()
        
        # Special case for quote list endpoint
        if isinstance(data, list):
            return {'results': data}
            
        # Special case for inflation and prime rate endpoints
        if any(key in data for key in ['inflation', 'prime-rate']):
            return data
            
        if 'results' not in data:
            logger.error("No results found in response")
            return None
            
        results = data['results']
        if not results:
            logger.warning("Empty results in response")
            return data

        # Handle both list and dict formats
        if isinstance(results, dict):
            results = [results]
        elif not isinstance(results, list):
            logger.error(f"Unexpected results format: {type(results)}")
            return None

        # For financial data, ensure we have the right structure
        if expected_module:
            for result in results:
                if expected_module not in result:
                    logger.warning(f"Module {expected_module} not found in response")
                    continue
                    
                module_data = result[expected_module]
                if isinstance(module_data, dict):
                    # Handle nested data structures for balance sheets
                    if expected_module in ['balanceSheetHistory', 'balanceSheetHistoryQuarterly']:
                        if 'balanceSheetStatements' in module_data:
                            result[expected_module] = module_data['balanceSheetStatements']
                        else:
                            result[expected_module] = [module_data]
                    # Handle nested data structures for income statements
                    elif expected_module in ['incomeStatementHistory', 'incomeStatementHistoryQuarterly']:
                        if 'incomeStatementHistory' in module_data:
                            result[expected_module] = module_data['incomeStatementHistory']
                        else:
                            result[expected_module] = [module_data]
                    # Handle other financial data
                    elif expected_module in ['financialData', 'defaultKeyStatistics']:
                        result[expected_module] = module_data

        return {
            'results': results,
            'requestedAt': data.get('requestedAt', ''),
            'took': data.get('took', '')
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        return None

@tool
def get_income_statements(tickers: Union[str, List[str]], range: str = '5y') -> Optional[Dict]:
    """Get income statements for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            raise ValueError("BRAPI_TOKEN not found in environment variables")

        # Convert single ticker to list
        if isinstance(tickers, str):
            tickers = [tickers]

        # Validate range
        range = validate_range(range)

        results = {}
        for ticker in tickers:
            url = f"{BASE_URL}/quote/{ticker}"
            params = {
                'token': API_KEY,
                'range': range,
                'fundamental': 'true',
                'modules': 'incomeStatementHistory'
            }

            response = requests.get(url, params=params)
            data = handle_brapi_response(response)
            
            if data and 'results' in data and data['results']:
                result = data['results'][0]
                if 'incomeStatementHistory' in result:
                    results[ticker] = result['incomeStatementHistory']
                else:
                    logger.warning(f"No income statement data found for {ticker}")

        return results if results else None

    except Exception as e:
        logger.error(f"Error getting income statements: {str(e)}")
        return None

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
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                # Validate each quote
                validated_data = []
                for quote in data:
                    try:
                        validated_quote = StockQuote(**quote)
                        validated_data.append(validated_quote.model_dump())
                    except Exception as e:
                        logger.warning(f"Invalid quote data: {str(e)}")
                return {'stocks': pd.DataFrame(validated_data)}
            else:
                logger.error("Unexpected data format: Expected a list")
                return {'stocks': pd.DataFrame()}
        
        logger.error(f"Request failed with status code {response.status_code}")
        return {'stocks': pd.DataFrame()}
            
    except Exception as e:
        logger.error(f"Error fetching quote list: {str(e)}")
        return {'stocks': pd.DataFrame()}

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
        
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        range_value = validate_range(range)
        interval_value = validate_interval(interval)
        
        params = {
            'token': API_KEY,
            'range': range_value,
            'interval': interval_value,
            'fundamental': 'true' if fundamental else 'false'
        }
        
        response = requests.get(url, params=params)
        result = handle_brapi_response(response)
        
        if result:
            # Validate quote data
            validated_results = []
            for quote in result['results']:
                try:
                    validated_quote = StockQuote(**quote)
                    validated_results.append(validated_quote.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid quote data for {quote.get('symbol', 'unknown')}: {str(e)}")
            result['results'] = validated_results
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching quote data: {str(e)}")
        return None

@tool
def get_balance_sheet_history(tickers: Union[str, List[str]], range: str = '5y') -> Optional[Dict]:
    """Get balance sheet history for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            raise ValueError("BRAPI_TOKEN not found in environment variables")

        # Convert single ticker to list
        if isinstance(tickers, str):
            tickers = [tickers]

        # Validate range
        range = validate_range(range)

        results = {}
        for ticker in tickers:
            url = f"{BASE_URL}/quote/{ticker}"
            params = {
                'token': API_KEY,
                'range': range,
                'fundamental': 'true',
                'modules': 'balanceSheetHistory'
            }

            response = requests.get(url, params=params)
            data = handle_brapi_response(response, 'balanceSheetHistory')
            
            if data and 'results' in data and data['results']:
                result = data['results'][0]
                if 'balanceSheetHistory' in result:
                    statements = result['balanceSheetHistory']
                    if isinstance(statements, list):
                        results[ticker] = statements
                    else:
                        logger.warning(f"Unexpected balance sheet data format for {ticker}")
                else:
                    logger.warning(f"No balance sheet data found for {ticker}")

        return results if results else None

    except Exception as e:
        logger.error(f"Error getting balance sheet history: {str(e)}")
        return None

@tool
def get_financial_data(tickers: Union[str, List[str]]) -> Optional[Dict]:
    """Get key financial metrics for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'fundamental': 'true',
            'modules': get_module_list('financial_data', 'summary_profile')
        }
        
        response = requests.get(url, params=params)
        result = handle_brapi_response(response, BRAPI_MODULES['financial_data'])
        
        if result:
            # Validate financial data
            for ticker_data in result.values():
                if BRAPI_MODULES['financial_data'] in ticker_data:
                    FinancialDataItem(**ticker_data[BRAPI_MODULES['financial_data']])
                else:
                    logger.warning(f"No financial data found for some tickers")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching financial data: {str(e)}")
        return None

@tool
def get_default_key_statistics(tickers: Union[str, List[str]]) -> Optional[Dict]:
    """Get key statistics for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if isinstance(tickers, str):
            tickers = [tickers]
            
        ticker_str = ','.join(tickers)
        url = f"{BASE_URL}/quote/{ticker_str}"
        
        params = {
            'token': API_KEY,
            'fundamental': 'true',
            'modules': get_module_list('key_statistics', 'summary_profile')
        }
        
        response = requests.get(url, params=params)
        result = handle_brapi_response(response, BRAPI_MODULES['key_statistics'])
        
        if result:
            # Validate key statistics data
            for ticker_data in result.values():
                if BRAPI_MODULES['key_statistics'] in ticker_data:
                    KeyStatistics(**ticker_data[BRAPI_MODULES['key_statistics']])
                else:
                    logger.warning(f"No key statistics found for some tickers")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching key statistics: {str(e)}")
        return None

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
        result = handle_brapi_response(response)
        
        if result and 'inflation' not in result:
            logger.warning("No inflation data found in response")
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching inflation data: {str(e)}")
        return None

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
        result = handle_brapi_response(response)
        
        if result and 'prime-rate' not in result:
            logger.warning("No prime rate data found in response")
            
        return result
        
    except Exception as e:
        logger.error(f"Error fetching prime rate data: {str(e)}")
        return None

@tool
def get_income_statement_history_quarterly(tickers: Union[str, List[str]], range: str = '5y') -> Optional[Dict]:
    """Get quarterly income statement history for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            raise ValueError("BRAPI_TOKEN not found in environment variables")

        # Convert single ticker to list
        if isinstance(tickers, str):
            tickers = [tickers]

        # Validate range
        range = validate_range(range)

        results = {}
        for ticker in tickers:
            url = f"{BASE_URL}/quote/{ticker}"
            params = {
                'token': API_KEY,
                'range': range,
                'fundamental': 'true',
                'modules': 'incomeStatementHistoryQuarterly'
            }

            response = requests.get(url, params=params)
            data = handle_brapi_response(response)
            
            if data and 'results' in data and data['results']:
                result = data['results'][0]
                if 'incomeStatementHistoryQuarterly' in result:
                    results[ticker] = result['incomeStatementHistoryQuarterly']
                else:
                    logger.warning(f"No quarterly income statement data found for {ticker}")

        return results if results else None

    except Exception as e:
        logger.error(f"Error getting quarterly income statement history: {str(e)}")
        return None

@tool
def get_balance_sheet_history_quarterly(tickers: Union[str, List[str]], range: str = '5y') -> Optional[Dict]:
    """Get quarterly balance sheet history for Brazilian stocks."""
    try:
        load_dotenv(override=True)
        BASE_URL = "https://brapi.dev/api"
        API_KEY = os.getenv("BRAPI_TOKEN")
        
        if not API_KEY:
            raise ValueError("BRAPI_TOKEN not found in environment variables")

        # Convert single ticker to list
        if isinstance(tickers, str):
            tickers = [tickers]

        # Validate range
        range = validate_range(range)

        results = {}
        for ticker in tickers:
            url = f"{BASE_URL}/quote/{ticker}"
            params = {
                'token': API_KEY,
                'range': range,
                'fundamental': 'true',
                'modules': 'balanceSheetHistoryQuarterly'
            }

            response = requests.get(url, params=params)
            data = handle_brapi_response(response, 'balanceSheetHistoryQuarterly')
            
            if data and 'results' in data and data['results']:
                result = data['results'][0]
                if 'balanceSheetHistoryQuarterly' in result:
                    statements = result['balanceSheetHistoryQuarterly']
                    if isinstance(statements, list):
                        results[ticker] = statements
                    else:
                        logger.warning(f"Unexpected quarterly balance sheet data format for {ticker}")
                else:
                    logger.warning(f"No quarterly balance sheet data found for {ticker}")

        return results if results else None

    except Exception as e:
        logger.error(f"Error getting quarterly balance sheet history: {str(e)}")
        return None

