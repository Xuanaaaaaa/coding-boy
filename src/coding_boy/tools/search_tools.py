from .registry import tool
import subprocess
from typing import Annotated, Optional
import requests
from bs4 import BeautifulSoup

MAX_WEB_LENGTH = 50000

@tool
def grep_search(
    pattern: Annotated[
        str,
        "搜索关键词或正则表达式，例如 UserService、createOrder"
    ],
    path: Annotated[
        str,
        "搜索目录路径，默认为当前目录，例如 ./src"
    ] = ".",
    include: Annotated[
        Optional[str],
        "文件过滤规则，例如 *.java、*.py，用于限制搜索文件类型，默认不过滤"
    ] = None,
    exclude_dirs: Annotated[
        list[str],
        """
        默认忽略目录: .git、node_modules、target、build、dist、.idea。
        如果需要搜索这些目录，可以传入新的忽略列表覆盖默认值，但要注意：新传入的列表会完全覆盖默认目录
        """
    ] = [
        ".git",
        "node_modules",
        "target",
        "build",
        "dist",
        ".idea",
    ],
    hidden: Annotated[
        bool,
        "是否搜索隐藏文件，例如 .env、.github，默认为否"
    ] = False,
    max_results: Annotated[
        int,
        "最多返回多少条搜索结果，防止返回内容过大，默认50条"
    ] = 50,
) -> str:
    """
    使用 ripgrep 搜索代码内容。
    默认忽略常见依赖目录和构建产物目录。
    """
    try:
        args = ["rg", "--line-number", "--color=never", "--no-heading", "--max-count", str(max_results)]
        for directory in exclude_dirs:
            args.extend(["--glob", f"!{directory}"])
        if hidden:
            args.append("--hidden")
        if include:
            args.extend(["--glob", include])
        args.extend(["--", pattern, path])
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 1:
            return "No matches found."
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        lines = [
            line
            for line in result.stdout.splitlines()
            if line
        ]
        output = "\n".join(lines[:max_results])
        if len(lines) > max_results:
            output += f"\n... and {len(lines) - max_results} more matches"
        return output
    except subprocess.TimeoutExpired:
        return "Error: search timeout."
    except Exception as e:
        return f"Error: {e}"

@tool(deferred=True)
def web_search(
    url: Annotated[str, "需要抓取网页的 URL，例如 https://example.com"],
    max_length: Annotated[int, "网页内容最大返回字符数，默认 50000，超过部分会被截断，避免占用过多上下文"] = MAX_WEB_LENGTH,
) -> str:
    """
    获取网页内容。
    功能：
    1. 请求 URL 获取网页内容
    2. 自动识别 HTML
    3. 移除 script/style 标签
    4. 提取纯文本
    5. 限制返回长度
    Args:
        url: 网页地址
        max_length: 最大返回字符数量
    Returns:
        网页文本内容
    """
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "coding-boy/1.0"
            },
            timeout=30,
        )
        if not response.ok:
            return (
                f"HTTP error: "
                f"{response.status_code} {response.reason}"
            )
        text = response.text
        content_type = response.headers.get("Content-Type", "")
        # HTML 内容清洗
        if "html" in content_type.lower():
            soup = BeautifulSoup(text, "html.parser")
            # 删除无意义标签
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            # 获取正文文本
            text = soup.get_text(separator=" ", strip=True)
        # 压缩连续空白
        text = " ".join(text.split())
        # 长度限制
        if len(text) > max_length:
            text = (text[:max_length] + f"\n\n[... truncated at {max_length} characters]")
        return text or "(empty response)"
    except requests.Timeout:
        return "Error: Request timed out (30s)"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"