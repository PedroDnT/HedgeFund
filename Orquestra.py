from langchain_core.tools import tool
from typing import List, Dict, Optional, Union
import requests
import os
from pydantic import BaseModel, Field
import pandas as pd
import ta
from datetime import datetime, timedelta
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
from typing import Literal, Sequence, List, Annotated
import logging
import functools
import operator
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[RichHandler()]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Validate all required API keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN")

logger.debug(f"BRAPI_TOKEN loaded: {'yes' if BRAPI_TOKEN else 'no'}")
logger.debug(f"TAVILY_API_KEY loaded: {'yes' if TAVILY_API_KEY else 'no'}")

if BRAPI_TOKEN:
    logger.debug(f"BRAPI_TOKEN value: {BRAPI_TOKEN[:5]}...")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
if not BRAPI_TOKEN:
    raise ValueError("BRAPI_TOKEN not found in environment variables")
if BRAPI_TOKEN == '<your_actual_brapi_token>':
    raise ValueError("BRAPI_TOKEN is still set to placeholder value. Please update with actual token")

# Import all tools from tools.py
from tools import (
    get_income_statements,
    get_income_statement_history_quarterly,
    get_balance_sheet_history,
    get_balance_sheet_history_quarterly,
    get_quote,
    get_quote_list,
    get_financial_data,
    get_default_key_statistics,
    get_inflation,
    get_prime_rate
)

# Group tools by category for better organization
financial_statement_tools = [
    get_income_statements,
    get_income_statement_history_quarterly,
    get_balance_sheet_history,
    get_balance_sheet_history_quarterly
]

market_data_tools = [
    get_quote,
    get_quote_list,
]

analysis_tools = [
    get_financial_data,
    get_default_key_statistics
]

economic_tools = [
    get_inflation,
    get_prime_rate
]

# Initialize Tavily search tool with API key from environment
get_news_tool = TavilySearchResults(
    api_key=TAVILY_API_KEY,
    max_results=5
)

# Combine all tools for agent use
all_tools = [
    *financial_statement_tools,
    *market_data_tools,
    *analysis_tools,
    *economic_tools,
    get_news_tool
]

# Define team members
members = ["fundamental_analyst", "valuation_analyst", "price_analyst"]

# Create the routing prompt template with detailed analyst behaviors
routing_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a portfolio manager supervising a hedge fund team with the following analysts:

        1. fundamental_analyst: Analyzes financial statements and company health
        -	Collect data: Retrieve income statements and balance sheets over multiple periods.
        -	Must calculate key ratios: Profitability, liquidity, leverage, and efficiency.
        -	Analyze trends: Identify improvements or declines across periods.
        -	Evaluate financial health: Summarize insights on stability and risk.
        -	Provide recommendations: Suggest actions based on findings.
        -   Focus on the most important insights and recommendations and output just relevant data
        -   Explain insights grounded only on the data you retrieved, not from other sources
        - Important:Altough you will be prompted to perform an analysis that is broader than your scope, only output analysis insights according to your scope outlined above.
        - Only output fundamental analysis insights, not valuation analysis insights.
        - Only use data provided by the get_balance_sheet_history, get_income_statements, get_balance_sheet_history_quarterly and get_income_statement_history_quarterly tools.
        
        2. valuation_analyst: Analyzes market data and valuation ratios
        - Extract data: Use key metrics from defaultKeyStatistics, including valuation, profitability, and growth indicators.
        - Interpret metrics: Analyze the provided ratios to evaluate the company’s financial and operational standing.
        - Summarize insights: Provide a clear overview of the company’s valuation and potential risks or opportunities.
        - Focus on the most important insights and data and recommendations and output just relevant data
        - Explain insights grounded only on the data you retrieved, not from other sources
        - Important:Altough you will be prompted to perform an analysis that is broader than your scope, only output analysis insights according to your scope outlined above.
        - Only output valuation analysis insights, not fundamental analysis insights.
        - Only use data provided by the get_default_key_statistics and get_financial_data tools.

        3. price_analyst: Analyzes price action and trends
        - Focuses on price evolution and price patterns
        - Studies price movements, support/resistance levels
        - Analyzes momentum 
        - Identifies trading opportunities based on price action
        - Focus on the most important insights and data and recommendations and output just relevant data
        - Explain insights grounded only on the data you retrieved, not from other sources
        - Important:Altough you will be prompted or recieve data to perform an analysis that is broader than your scope, only output price analysis insights according to your scope outlined above.
        - Only output price analysis insights, not fundamental or valuation analysis insights.
        - Only use data provided by the get_quote tool.`
        
        Determine which analyst(s) should analyze the request. Respond with ONLY the analyst names
        separated by commas (e.g., 'fundamental_analyst,valuation_analyst,price_analyst')."""
    ),
    MessagesPlaceholder(variable_name="messages"),
])

# Create the summary prompt template
summary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a portfolio manager responsible for synthesizing analysis from your team of analysts.
        Review all the analysts' reports and provide a comprehensive summary including:
        1. Key financial metrics and their implications (only when you have this data)
        2. Price analysis insights (only when you have this data)
        3. Market data insights (only when you have this data)
        4. Overall investment recommendation
        5. Focus on the most important insights and recommendations and output just relevant data
        6. Explain insights grounded in the data
        Make sure to:
        - Be analytical on the data 
        - Be concise and to the point
        - Consider both bullish and bearish signals
        - Provide clear actionable recommendations
        - Identify key risks and potential catalysts"""
    ),
    MessagesPlaceholder(variable_name="messages"),
    (
        "human",
        "Based on all the analyst reports above, provide a comprehensive summary and investment recommendation."
    ),
])

# Initialize the language model
llm = ChatOpenAI(model="gpt-4o-mini")

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    selected_analysts: List[str]
    current_analyst_idx: int
    error_count: int
    completed_analyses: List[str]

def supervisor_router(state):
    """Route to appropriate analyst(s) based on the query"""
    # Create the routing chain
    routing_chain = routing_prompt | llm

    # Get the routing decision
    result = routing_chain.invoke(state)
    selected_analysts = [a.strip() for a in result.content.strip().split(',')]

    # Add routing message to state
    message = SystemMessage(
        content=f"Routing query to: {', '.join(selected_analysts)}",
        name="supervisor"
    )

    return {
        "messages": state["messages"] + [message],
        "selected_analysts": selected_analysts,
        "current_analyst_idx": 0
    }

def get_next_step(state):
    """Determine the next step in the workflow"""
    if not state["selected_analysts"]:
        return "final_summary"

    current_idx = state["current_analyst_idx"]
    if current_idx >= len(state["selected_analysts"]):
        return "final_summary"

    return state["selected_analysts"][current_idx]

def agent_node(state, agent, name):
    """Generic analyst node that updates the current_analyst_idx after completion"""
    result = agent.invoke(state)

    return {
        "messages": state["messages"] + [HumanMessage(content=result["messages"][-1].content, name=name)],
        "selected_analysts": state["selected_analysts"],
        "current_analyst_idx": state["current_analyst_idx"] + 1
    }

def final_summary_agent(state):
    """Create final summary of all analyst reports"""
    summary_chain = summary_prompt | llm
    result = summary_chain.invoke(state)
    return {
        "messages": state["messages"] + [HumanMessage(content=result.content, name="portfolio_manager")],
        "selected_analysts": state["selected_analysts"],
        "current_analyst_idx": state["current_analyst_idx"]
    }

# Create the agents with appropriate tools
fundamental_analyst = create_react_agent(
    llm, 
    tools=[get_balance_sheet_history, get_income_statements, get_balance_sheet_history_quarterly, get_income_statement_history_quarterly]
)

valuation_analyst = create_react_agent(
    llm, 
    tools=[get_default_key_statistics, get_financial_data]
)

price_analyst = create_react_agent(
    llm, 
    tools=[get_quote]
)

# Create the agent nodes
fundamental_analyst_node = functools.partial(agent_node, agent=fundamental_analyst, name="fundamental_analyst")
valuation_analyst_node = functools.partial(agent_node, agent=valuation_analyst, name="valuation_analyst")
price_analyst_node = functools.partial(agent_node, agent=price_analyst, name="price_analyst")

# Initialize workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_router)
workflow.add_node("fundamental_analyst", fundamental_analyst_node)
workflow.add_node("valuation_analyst", valuation_analyst_node)
workflow.add_node("price_analyst", price_analyst_node)
workflow.add_node("final_summary", final_summary_agent)

# Add conditional edges
workflow.add_conditional_edges(
    "supervisor",
    get_next_step,
    {
        "fundamental_analyst": "fundamental_analyst",
        "valuation_analyst": "valuation_analyst",
        "price_analyst": "price_analyst",
        "final_summary": "final_summary"
    }
)

# Add edges from analysts back to router
for analyst in members:
    workflow.add_conditional_edges(
        analyst,
        get_next_step,
        {
            "fundamental_analyst": "fundamental_analyst",
            "valuation_analyst": "valuation_analyst",
            "price_analyst": "price_analyst",
            "final_summary": "final_summary"
        }
    )

# Add entry and exit edges
workflow.add_edge(START, "supervisor")
workflow.add_edge("final_summary", END)

# Compile graph
graph = workflow.compile()

# Run the workflow
# try:
#     response = graph.invoke({
#         "messages": [HumanMessage(content="Analyze PETR4's recent financials and market data")],
#         "selected_analysts": [],
#         "current_analyst_idx": 0,
#         "error_count": 0,
#         "completed_analyses": []
#     })
# except Exception as e:
#     logger.error(f"Workflow execution failed: {str(e)}")

from prettyprint import stream_agent_execution


input_data = {
    "messages": [HumanMessage(content="What is PETR4's current financial health and how has its price been performing?")]
}
config = {"recursion_limit": 10}
stream_agent_execution(graph, input_data, config)