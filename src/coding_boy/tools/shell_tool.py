from .registry import tool
from typing import Annotated
import subprocess

@tool
def run_shell(command: Annotated[str, "要执行的shell命令参数"], timeout: Annotated[int, "最大超时时间, 默认时间为30s"] = 30) -> str:
    """
    用于执行shell命令
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr = f"\nStderr: {result.stderr}" if result.stderr else ""
            stdout = f"\nStdout: {result.stdout}" if result.stdout else ""
            return f"Command failed (exit code {result.returncode}){stdout}{stderr}"
        return result.stdout or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"
