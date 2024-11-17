# Hedge Fund Agent Team for Brazilian Markets

An adaptation of [virattt's hedge-fund-agent-team](https://gist.github.com/virattt/0e4c7740472177a327b61449c9af721d), modified to analyze Brazilian market stocks using BRAPI API. The project implements a multi-agent system where each agent specializes in different aspects of financial analysis.

## Project Structure

- **Orquestra.py**: Main orchestration file that:
  - Configures and manages the agent team
  - Defines agent roles and behaviors
  - Handles the workflow between agents
  - Processes user queries and generates final analysis

- **tools.py**: Contains all BRAPI API tool implementations:
  - Financial statement tools (income statements, balance sheets)
  - Market data tools (quotes, listings)
  - Analysis tools (key statistics, financial data)
  - Economic indicators (inflation, prime rate)

- **prettyprint.py**: Handles output formatting:
  - Rich text formatting for terminal output
  - Custom styling for different message types
  - Organized display of analysis results

- **brapi_wrapper.py**: API wrapper interface:
  - Imports tools from tools.py
  - Provides high-level access to BRAPI endpoints

## Key Features

- **Multi-Agent Analysis**:
  - Fundamental Analyst: Financial statements and company health
  - Valuation Analyst: Market data and valuation ratios
  - Price Analyst: Price action and trends

- **BRAPI Integration**:
  - Real-time market data
  - Historical financial statements
  - Company statistics and metrics

- **Rich Output Formatting**:
  - Color-coded analysis sections
  - Clear visual hierarchy
  - Organized data presentation

## Requirements

- Python 3.8+
- BRAPI API Key
- Required packages:
  ```python
  langchain
  langgraph
  rich
  pandas
  requests
  python-dotenv
  ```

## Installation

1. Clone the repository:
```bash
git clone <https://github.com/PedroDnT/HedgeFund>
cd <repository-directory>

```

2. Install dependencies:
```bash
pip install -r requirements.txt

```

3. Configure environment variables:

## Usage

Run the main orchestration script:
```bash
python Orquestra.py
```
Example query:
"What is PETR4's current financial health and how has its price been performing?"


## Data Flow

1. User query → Orquestra.py
2. Query routed to appropriate analysts
3. Analysts use tools.py to fetch data via BRAPI
4. Analysis results formatted by prettyprint.py
5. Final comprehensive analysis presented to user

## License

MIT License

## Acknowledgments

- Original concept by [virattt](https://gist.github.com/virattt)
- Powered by [BRAPI](https://brapi.dev/) for Brazilian market data
- Built with LangGraph for agent orchestration
