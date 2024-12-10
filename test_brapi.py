import requests
import os
from dotenv import load_dotenv
import json
from pprint import pprint

# Load environment variables
load_dotenv(override=True)
API_KEY = os.getenv("BRAPI_TOKEN")
BASE_URL = "https://brapi.dev/api"

def test_quote(ticker="PETR4"):
    """Test basic quote endpoint"""
    print("\n=== Testing Quote Endpoint ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'range': '1d',
        'interval': '1d',
        'fundamental': 'true'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())

def test_financial_statements(ticker="PETR4"):
    """Test financial statements endpoint"""
    print("\n=== Testing Financial Statements ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'range': '1y',
        'fundamental': 'true',
        'modules': 'incomeStatementHistory,balanceSheetHistory'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())

def test_financial_data(ticker="PETR4"):
    """Test financial data endpoint"""
    print("\n=== Testing Financial Data ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'fundamental': 'true',
        'modules': 'financialData,defaultKeyStatistics'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())

def test_quote_list():
    """Test quote list endpoint"""
    print("\n=== Testing Quote List ===")
    url = f"{BASE_URL}/quote/list"
    params = {
        'token': API_KEY,
        'limit': 5
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        pprint(response.json())

def test_available_modules(ticker="PETR4"):
    """Test all available modules"""
    print("\n=== Testing All Available Modules ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'fundamental': 'true',
        'modules': 'summaryProfile,balanceSheetHistory,balanceSheetHistoryQuarterly,incomeStatementHistory,incomeStatementHistoryQuarterly,financialData,defaultKeyStatistics'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            print("\nAvailable modules:")
            for module in result.keys():
                print(f"- {module}")

def test_historical_data(ticker="PETR4"):
    """Test historical data endpoint"""
    print("\n=== Testing Historical Data ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'range': '1mo',
        'interval': '1d'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            if 'historicalDataPrice' in result:
                print(f"\nHistorical data points: {len(result['historicalDataPrice'])}")
                if result['historicalDataPrice']:
                    print("\nSample data point:")
                    pprint(result['historicalDataPrice'][0])

def test_balance_sheet_data(ticker="PETR4"):
    """Test balance sheet data endpoint with detailed logging"""
    print("\n=== Testing Balance Sheet Data ===")
    url = f"{BASE_URL}/quote/{ticker}"
    params = {
        'token': API_KEY,
        'range': '1y',
        'fundamental': 'true',
        'modules': 'balanceSheetHistory'
    }
    
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("\nFull Response Structure:")
        pprint(data)
        
        if 'results' in data and data['results']:
            result = data['results'][0]
            print("\nBalance Sheet Keys:")
            pprint(list(result.keys()))
            
            if 'balanceSheetHistory' in result:
                print("\nBalance Sheet History Structure:")
                pprint(result['balanceSheetHistory'])
            else:
                print("\nNo balanceSheetHistory found in result")
        else:
            print("\nNo results found in response")

if __name__ == "__main__":
    # Test balance sheet data specifically
    test_balance_sheet_data()
    
    # Run other tests
    test_quote()
    test_quote_list()
    test_financial_statements()
    test_financial_data()
    test_available_modules()
    test_historical_data() 