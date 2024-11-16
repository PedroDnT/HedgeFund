from typing import Union, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.syntax import Syntax
from rich.theme import Theme
from rich.style import Style
import json
import logging

# Custom theme for different roles
custom_theme = Theme({
    "supervisor": "bold magenta",
    "valuation_analyst": "bold green",
    "fundamental_analyst": "bold blue",
    "price_analyst": "bold yellow",
    "portfolio_manager": "bold red",
    "error": "bold red",
    "info": "bold cyan",
    "warning": "bold yellow",
    "success": "bold green"
})

# Define role-specific emojis and styles at module level
role_styles = {
    "supervisor": ("🎯", "magenta"),
    "valuation_analyst": ("📊", "green"),
    "fundamental_analyst": ("💰", "blue"),
    "price_analyst": ("📈", "yellow"),
    "portfolio_manager": ("👔", "red"),
    "user": ("❓", "bold white"),
    "assistant": ("🤖", "bold blue"),
    "system": ("⚙️", "dim"),
    "tool": ("🔧", "yellow")
}

console = Console(theme=custom_theme)

# Custom logging handler using Rich
class RichLoggingHandler(logging.Handler):
    def emit(self, record):
        # Skip debug messages from httpx, httpcore, etc
        if record.name.startswith(('httpx', 'httpcore', 'urllib3')):
            return
            
        # Create a styled message based on log level
        level_name = record.levelname.lower()
        message = record.getMessage()
        
        if level_name == 'error':
            console.print(f"[error]❌ {message}[/]")
        elif level_name == 'warning':
            console.print(f"[warning]⚠️ {message}[/]")
        elif level_name == 'info':
            console.print(f"[info]ℹ️ {message}[/]")
        elif level_name == 'debug':
            console.print(f"[dim]🔍 {message}[/]")

def format_json(data: Dict[str, Any]) -> str:
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2)

def format_code(code: str, language: str = "python") -> Syntax:
    """Format code blocks with syntax highlighting"""
    return Syntax(code, language, theme="monokai", line_numbers=True)

def format_error(error: str) -> Text:
    """Format error messages"""
    text = Text()
    text.append("❌ Error: ", style="error")
    text.append(error, style="red")
    return text

def format_message_content(content: str) -> Union[str, Text]:
    """Format message content with appropriate styling"""
    if not content:
        return Text("")
        
    try:
        # Try to parse as JSON for structured data
        data = json.loads(content)
        formatted_json = json.dumps(data, indent=2)
        text = Text(formatted_json)
        # Highlight keys in JSON
        text.highlight_regex(r'"[^"]+":(?=\s)', style="bold blue")
        # Highlight numbers
        text.highlight_regex(r'\b\d+\.?\d*\b', style="bold green")
        return text
    except json.JSONDecodeError:
        # If not JSON, return as formatted text
        text = Text(content)
        
        # Add styling for different elements
        # Numbers (including those with BRL prefix)
        text.highlight_regex(r'BRL\s*\d+\.?\d*|\b\d+\.?\d*%?\b', style="bold green")
        
        # Markdown-style headers
        text.highlight_regex(r'#{1,6}\s+.*$', style="bold cyan", multiline=True)
        
        # Markdown-style bold text
        text.highlight_regex(r'\*\*.*?\*\*', style="bold")
        
        # Important keywords
        keywords = ['revenue', 'price', 'profit', 'earnings', 'ratio', 'analysis', 'recommendation']
        for keyword in keywords:
            text.highlight_regex(f'\\b{keyword}\\b', style="italic", ignore_case=True)
        
        # Lists (bullet points)
        text.highlight_regex(r'^\s*[-•]\s+.*$', style="yellow", multiline=True)
        
        return text

def format_message(message: Dict[str, Any]) -> Panel:
    """Format a message as a Rich panel with role-specific styling"""
    role = message.get("role", "unknown")
    name = message.get("name", role)
    content = message.get("content", "")
    
    emoji, style = role_styles.get(name, ("💬", "bold white"))
    
    # Format title based on message type
    title = f"{emoji} {name.replace('_', ' ').title()}"
    if "Routing" in str(content):
        title = f"{emoji} Routing Decision"
    
    # Handle tool calls
    if "tool_calls" in message:
        tool_calls = message.get("tool_calls", [])
        content = "Tool Calls:\n" + "\n".join([
            f"- {tool.get('function', {}).get('name')}: {tool.get('function', {}).get('arguments')}"
            for tool in tool_calls
        ])
    
    formatted_content = format_message_content(content)
    
    # Add metadata if available
    metadata = []
    if "timestamp" in message:
        metadata.append(f"Time: {message['timestamp']}")
    if "tool_name" in message:
        metadata.append(f"Tool: {message['tool_name']}")
        
    subtitle = " | ".join(metadata) if metadata else None
    
    return Panel(
        formatted_content,
        title=title,
        subtitle=subtitle,
        border_style=style,
        padding=(1, 2),
        highlight=True
    )

def stream_agent_execution(graph, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
    """Stream the execution of an agent graph with pretty printing"""
    try:
        # Configure root logger with Rich handler
        root_logger = logging.getLogger()
        root_logger.handlers = []
        rich_handler = RichLoggingHandler()
        root_logger.addHandler(rich_handler)
        
        # Print initial separator and user query
        console.print(Rule("🚀 Starting Analysis", style="bold cyan"))
        if "messages" in input_data and input_data["messages"]:
            user_message = input_data["messages"][0]
            console.print(Panel(
                user_message.content,
                title="❓ User Query",
                border_style="bold white",
                padding=(1, 2)
            ))
        
        # Track the current step for better visualization
        current_step = 1
        
        for output in graph.stream(input_data, config):
            if isinstance(output, dict):
                # Get the node name (key) and its output (value)
                for node_name, node_output in output.items():
                    # Print supervisor routing
                    if node_name == "supervisor" and "selected_analysts" in node_output:
                        analysts = node_output.get("selected_analysts", [])
                        if analysts:
                            console.print("\n[bold magenta]🎯 Supervisor Decision:[/]")
                            console.print("   Routing query to:")
                            for analyst in analysts:
                                console.print(f"   [magenta]→[/] [bold]{analyst}[/]")
                            console.print()
                    
                    # Print analyst responses
                    elif node_name in ["valuation_analyst", "fundamental_analyst", "price_analyst"]:
                        if "messages" in node_output:
                            messages = node_output["messages"]
                            for message in messages:
                                # Handle different message types
                                if hasattr(message, 'name') and hasattr(message, 'content'):
                                    name = message.name if hasattr(message, 'name') else node_name
                                    if name == node_name and message.content:
                                        title_emoji = {
                                            "valuation_analyst": "📊",
                                            "fundamental_analyst": "💰",
                                            "price_analyst": "📈"
                                        }.get(node_name, "🔍")
                                        
                                        console.print(Panel(
                                            message.content,
                                            title=f"{title_emoji} {node_name.replace('_', ' ').title()} Analysis",
                                            border_style=role_styles.get(node_name, "blue")[1],
                                            padding=(1, 2)
                                        ))
                                        console.print()
                    
                    # Print final summary
                    elif node_name == "final_summary":
                        if "messages" in node_output:
                            final_message = next(
                                (msg for msg in node_output["messages"] 
                                 if hasattr(msg, 'name') and msg.name == "portfolio_manager"),
                                None
                            )
                            if final_message:
                                console.print("\n[bold cyan]📊 Final Analysis:[/]")
                                console.print(Panel(
                                    final_message.content,
                                    border_style="cyan",
                                    padding=(1, 2)
                                ))
                                console.print()
                
                # Print any errors
                if "error" in output:
                    console.print(Panel(
                        str(output["error"]),
                        title="❌ Error",
                        border_style="red",
                        padding=(1, 2)
                    ))
                
    except Exception as e:
        console.print(format_error(f"Error in stream execution: {str(e)}"))
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/]")
        
    finally:
        # Print final separator
        console.print(Rule("✨ Analysis Complete", style="bold cyan"))