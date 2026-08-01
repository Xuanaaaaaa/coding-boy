from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

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
    tips.append("  • Type ", style="dim")
    tips.append("/mode", style="cyan")
    tips.append(" to switch permission mode\n", style="dim")

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


def print_confirmation(command: str) -> None:
    """打印危险操作确认提示"""
    console.print()
    console.print(Panel(
        f"[red]⚠ Dangerous Operation Detected[/red]\n\n[bold]{command}[/bold]",
        title="[yellow]Confirmation Required[/yellow]",
        border_style="yellow",
        padding=(1, 2)
    ))


# 权限模式描述
PERMISSION_MODES = {
    "default": "Normal mode. Dangerous operations require confirmation.",
    "plan": "Plan mode. Only edits to the plan file are allowed.",
    "acceptEdits": "Auto-accept edits. Dangerous commands still require confirmation.",
    "dontAsk": "Silent mode. Dangerous operations are auto-denied without prompting.",
    "bypassPermissions": "Bypass all checks. Use with caution!",
}


def select_permission_mode() -> str:
    """让用户选择权限模式"""
    console.print()
    console.print("[bold yellow]Permission Modes:[/bold yellow]")
    for i, (mode, desc) in enumerate(PERMISSION_MODES.items(), 1):
        console.print(f"  [cyan]{i}.[/cyan] [bold]{mode}[/bold]: {desc}")
    console.print()

    choices = [str(i) for i in range(1, len(PERMISSION_MODES) + 1)]
    choice = Prompt.ask(
        "Select mode",
        choices=choices,
        default="1"
    )

    mode_names = list(PERMISSION_MODES.keys())
    return mode_names[int(choice) - 1]
