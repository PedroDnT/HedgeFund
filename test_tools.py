from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, model_validator
import logging
from datetime import datetime, timedelta
from rich import print
from rich.console import Console
from rich.table import Table
import json
from tools import (
    get_income_statements,
    get_quote_list,
    get_quote,
    get_balance_sheet_history,
    get_financial_data,
    get_default_key_statistics,
    get_inflation,
    get_prime_rate,
    get_income_statement_history_quarterly,
    get_balance_sheet_history_quarterly
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
console = Console()

# Response Models
class HistoricalDataPrice(BaseModel):
    date: int
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    adjustedClose: Optional[float] = None

class CashDividend(BaseModel):
    assetIssued: str
    paymentDate: str
    rate: float
    relatedTo: str
    approvedOn: str
    isinCode: str
    label: str
    lastDatePrior: str
    remarks: str

class StockDividend(BaseModel):
    assetIssued: str
    factor: float
    completeFactor: str
    approvedOn: str
    isinCode: str
    label: str
    lastDatePrior: str
    remarks: str

class DividendsData(BaseModel):
    cashDividends: Optional[List[CashDividend]] = []
    stockDividends: Optional[List[StockDividend]] = []
    subscriptions: Optional[List[Any]] = []

class StockQuote(BaseModel):
    symbol: str
    currency: Optional[str] = None
    shortName: Optional[str] = None
    longName: Optional[str] = None
    regularMarketPrice: Optional[float] = None
    regularMarketDayHigh: Optional[float] = None
    regularMarketDayLow: Optional[float] = None
    regularMarketVolume: Optional[int] = None
    regularMarketChange: Optional[float] = None
    regularMarketChangePercent: Optional[float] = None
    regularMarketTime: Optional[str] = None
    marketCap: Optional[float] = None
    historicalDataPrice: Optional[List[HistoricalDataPrice]] = None
    dividendsData: Optional[DividendsData] = None

    class Config:
        extra = "allow"  # Allow extra fields that we haven't modeled

class APIResponse(BaseModel):
    results: Union[List[Dict[str, Any]], Dict[str, Any]]
    requestedAt: str
    took: str

    @model_validator(mode='before')
    @classmethod
    def validate_results(cls, values):
        if not isinstance(values, dict):
            return values
        results = values.get('results')
        if results is None:
            return values
        # Handle both list and dict formats
        if isinstance(results, list):
            # List format is already correct
            pass
        elif isinstance(results, dict):
            # Convert dict to list format if needed
            values['results'] = [results]
        return values

class TestResults(BaseModel):
    function_name: str
    success: bool
    error_message: Optional[str]
    response_data: Optional[Dict]

def test_function(func, **kwargs) -> TestResults:
    """Generic function tester with error handling"""
    try:
        # Get the function name from the tool's name attribute
        func_name = func.name if hasattr(func, 'name') else str(func)
        
        # Call the tool's invoke method
        response = func.invoke(kwargs)
        
        # Validate response structure
        if response:
            try:
                if isinstance(response, dict):
                    if 'results' in response:
                        # Handle both list and dict results
                        results = response['results']
                        if isinstance(results, dict):
                            # Convert dict results to list format
                            response['results'] = [results]
                        APIResponse(**response)
                    elif any(key in response for key in ['inflation', 'prime-rate']):
                        # Special case for inflation and prime rate endpoints
                        pass
                    elif 'stocks' in response:
                        # Special case for quote list endpoint
                        pass
                    else:
                        logger.warning(f"Unexpected response structure for {func_name}")
                elif isinstance(response, list):
                    # Handle direct list responses
                    pass
                else:
                    logger.warning(f"Unexpected response type for {func_name}: {type(response)}")
            except Exception as e:
                logger.error(f"Response validation failed for {func_name}: {str(e)}")
                return TestResults(
                    function_name=func_name,
                    success=False,
                    error_message=f"Validation error: {str(e)}",
                    response_data=response
                )
        
        return TestResults(
            function_name=func_name,
            success=True if response else False,
            error_message=None if response else "No data returned",
            response_data=response
        )
    except Exception as e:
        return TestResults(
            function_name=func_name if 'func_name' in locals() else str(func),
            success=False,
            error_message=str(e),
            response_data=None
        )

def format_sample_data(data: Any) -> str:
    """Format sample data for display"""
    if isinstance(data, dict):
        if 'results' in data:
            results = data['results']
            if isinstance(results, list) and results:
                return f"List results with {len(results)} items - First item keys: {list(results[0].keys())[:5]}..."
            elif isinstance(results, dict):
                return f"Dict results with keys: {list(results.keys())[:5]}..."
        elif 'stocks' in data:
            stocks = data['stocks']
            return f"Stocks list with {len(stocks)} items"
        return f"Dict with keys: {list(data.keys())[:5]}..."
    elif isinstance(data, list):
        if not data:
            return "Empty list"
        first_item = data[0]
        if isinstance(first_item, dict):
            return f"List with {len(data)} items - First item keys: {list(first_item.keys())[:5]}..."
        return f"List with {len(data)} items of type {type(first_item).__name__}"
    return str(data)[:100] + "..."

def print_test_results(results: List[TestResults]):
    """Print test results in a formatted table"""
    table = Table(title="Function Test Results")
    table.add_column("Function", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Error", style="red")
    table.add_column("Sample Data", style="yellow")

    for result in results:
        status = "✅" if result.success else "❌"
        error = result.error_message or ""
        sample_data = format_sample_data(result.response_data)
        table.add_row(result.function_name, status, error, sample_data)

    console.print(table)

def main():
    test_ticker = "PETR4"
    test_tickers = ["PETR4", "VALE3"]
    results = []

    # Test each function with valid parameters according to BRAPI docs
    tests = [
        (get_quote_list, {"search": None, "limit": 5}),
        (get_quote, {"tickers": test_ticker, "range": "1mo", "interval": "1d"}),
        (get_income_statements, {"tickers": test_ticker, "range": "2y"}),
        (get_balance_sheet_history, {"tickers": test_ticker, "range": "2y"}),
        (get_financial_data, {"tickers": test_ticker}),
        (get_default_key_statistics, {"tickers": test_ticker}),
        (get_inflation, {"historical": True}),
        (get_prime_rate, {"historical": True}),
        (get_income_statement_history_quarterly, {"tickers": test_ticker, "range": "2y"}),
        (get_balance_sheet_history_quarterly, {"tickers": test_ticker, "range": "2y"})
    ]

    for func, params in tests:
        result = test_function(func, **params)
        results.append(result)

    print_test_results(results)

    # Save detailed results to file
    with open("test_results.json", "w") as f:
        json.dump(
            [result.model_dump() for result in results],
            f,
            indent=2,
            default=str
        )

if __name__ == "__main__":
    main() 