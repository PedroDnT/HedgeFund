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

