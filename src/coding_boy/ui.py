from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

console = Console()

# ANSI 颜色代码（兼容不用 rich 的场景）
CYAN = "\033[36m"
YELLOW = "\033[33m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_welcome():
    """打印欢迎信息"""
    # 使用 rich 打印美观的欢迎界面
    title = Text()
    title.append("Coding Boy", style="bold cyan")
    title.append(" v0.1.0", style="dim")

    subtitle = Text("A lightweight coding assistant CLI", style="dim")

    tips = Text()
    tips.append("Tips:\n", style="yellow")
    tips.append("  • Type your question and press Enter\n", style="dim")
    tips.append("  • Type ", style="dim")
    tips.append("exit", style="cyan")
    tips.append(" or ", style="dim")
    tips.append("quit", style="cyan")
    tips.append(" to exit\n", style="dim")
    tips.append("  • Type ", style="dim")
    tips.append("/clear", style="cyan")
    tips.append(" to clear conversation history\n", style="dim")

    console.print()
    console.print(Panel(title, subtitle=subtitle, border_style="cyan", padding=(1, 2)))
    console.print(tips)
    console.print()


def print_tool_call(name: str, args: dict) -> None:
    """打印工具调用"""
    console.print(f"\n  [yellow]⚙ {name}[/yellow][dim] {_summarize_args(args)}[/dim]")


def print_tool_result(name: str, result: str) -> None:
    """打印工具结果"""
    truncated = _truncate(result, max_len=500)
    console.print(f"[dim]{truncated}[/dim]")


def print_error(message: str) -> None:
    """打印错误信息"""
    console.print(f"[red]Error: {message}[/red]")


def print_info(message: str) -> None:
    """打印普通信息"""
    console.print(f"[dim]{message}[/dim]")

def print_retry(attempt: int, max_retries: int, reason: str) -> None:
    """打印重试信息"""
    console.print(f"[yellow]Retry {attempt}/{max_retries}[/yellow][dim]: {reason}[/dim]")

def _truncate(text: str, max_len: int = 500) -> str:
    """截断长文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n  ... ({len(text)} chars total)"



def _summarize_args(args: dict) -> str:
    """总结参数"""
    if not args:
        return ""
    keys = list(args.keys())[:3]  # 只显示前 3 个参数名
    return " ".join(keys)