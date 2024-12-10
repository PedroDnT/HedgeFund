from Orquestra import graph, HumanMessage
from prettyprint import stream_agent_execution
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Run financial analysis workflow')
    parser.add_argument('query', type=str, nargs='?', help='Analysis query (e.g., "Analyze PETR4\'s financials")')
    parser.add_argument('--recursion-limit', type=int, default=10, help='Maximum recursion depth')
    
    args = parser.parse_args()

    # If no query provided, read from stdin
    if not args.query:
        if sys.stdin.isatty():
            parser.print_help()
            return
        args.query = sys.stdin.read().strip()

    input_data = {
        "messages": [HumanMessage(content=args.query)]
    }
    
    config = {"recursion_limit": args.recursion_limit}
    
    stream_agent_execution(graph, input_data, config)

if __name__ == "__main__":
    main()