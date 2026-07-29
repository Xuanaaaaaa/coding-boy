import os
import re
import platform
import subprocess
from pathlib import Path

# @include解析的正则表达式
INCLUDE_REGEX = re.compile(
    r"^@include\s+(\./[^\s]+|~/[^\s]+|/[^\s]+)$",
    re.MULTILINE
)
MAX_INCLUDE_DEPTH = 5 # 最多嵌套层数，超过以后不再解析

#系统提示词静态部分，放到最前面始终不变，稳定命中缓存
STATIC_CORE = """You are Coding Boy, a small coding assistant CLI.
You help with software engineering tasks using the tools available to you.

# Doing tasks
 - Do not propose changes to code you haven't read. Read files first.
 - Do not create files unless necessary. Prefer editing existing files.
 - Avoid over-engineering. Only make changes that were requested.

# Executing actions with care
 - Prefer reversible actions. For risky or destructive ones (rm -rf, git push,
   dropping tables), confirm with the user before proceeding.

# Using your tools
 - Use read_file / edit_file / list_files / grep_search instead of shell cat,
   sed, ls, grep. Reserve run_shell for actual shell operations.
 - If several tool calls are independent, make them in parallel.

# Tone and style
 - Keep responses short and concise. Lead with the answer.
 - Reference code as file_path:line_number."""

# @include解析函数
def resolve_includes(
    content: str,
    base_path: str,
    visited: set[str] | None = None,
    depth: int = 0
) -> str:
    """
    解析 @include 引用文件

    支持:
    @include ./relative.md
    @include ~/home/file.md
    @include /absolute/path.md
    """

    if visited is None:
        visited = set()
    if depth >= MAX_INCLUDE_DEPTH: # 超过最大深度以后，@include语句将会被原样保留
        return content
    def replace_include(match: re.Match) -> str: # sub方法中每一个匹配成功的对象都是一个re.Match对象
        raw_path = match.group(1) # 忽略掉@include部分，取得第一个括号内部的匹配内容部分
        # 解析路径
        if raw_path.startswith("~/"):
            resolved = Path.home() / raw_path[2:]
        elif raw_path.startswith("/"):
            resolved = Path(raw_path)
        else:
            # ./relative
            resolved = Path(base_path) / raw_path
        resolved = resolved.resolve()
        resolved_str = str(resolved)
        # 循环引用检测
        if resolved_str in visited:
            return f"<!-- circular: {raw_path} -->"
        # 文件不存在
        if not resolved.exists():
            return f"<!-- not found: {raw_path} -->"
        try:
            visited.add(resolved_str)
            included = resolved.read_text(encoding="utf-8")
            return resolve_includes(
                included,
                str(resolved.parent),
                visited,
                depth + 1
            )
        except Exception:
            return f"<!-- error reading: {raw_path} -->"
    return INCLUDE_REGEX.sub(replace_include, content)

#将项目目录下的./.agent/rules/下的md文件全部读取进来
def load_rules_dir(directory: str) -> str:
    rules_dir = Path(directory) / ".agent" / "rules"
    if not rules_dir.exists():
        return ""
    files = sorted(
        file
        for file in rules_dir.iterdir()
        if file.name.endswith(".md")
    )
    parts: list[str] = []
    for file in files:
        content = file.read_text(encoding="utf-8")
        content = resolve_includes(content, str(rules_dir))
        parts.append(f"<!-- rule: {file.name} -->\n{content}")
    if parts:
        return "\n\n## Rules\n" + "\n\n".join(parts)
    return ""

# 从工作目录开始，一层层往上读取所有agent.md文件，后读的放到最前面。同时读取rules文件。
def load_agent_md() -> str:
    parts: list[str] = []
    d = Path.cwd().resolve()
    while True:
        f = d / "agent.md"
        if f.is_file():
            try:
                content = f.read_text()
                content = resolve_includes(content, str(d))  # @include 解析
                parts.insert(0, content)
            except Exception:
                pass
        parent = d.parent
        if parent == d:
            break
        d = parent
    rules = load_rules_dir(str(Path.cwd()))  # .agent/rules/*.md
    agents_md = "\n\n# Project Instructions (agent.md)\n" + "\n\n---\n\n".join(parts) if parts else ""
    return agents_md + rules

#读取git状态
def get_git_context() -> str:
    try:
        opts = {"encoding": "utf-8", "timeout": 3, "capture_output": True}
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], **opts).stdout.strip()
        log = subprocess.run(["git", "log", "--oneline", "-5"], **opts).stdout.strip()
        status = subprocess.run(["git", "status", "--short"], **opts).stdout.strip()
        result = f"\nGit branch: {branch}"
        if log:
            result += f"\nRecent commits:\n{log}"
        if status:
            result += f"\nGit status:\n{status}"
        return result
    except Exception:
        return ""

def build_dynamic_system_context() -> str:
    # 动态块：环境 + git + 记忆 + 技能 + agent 列表
    plat = f"{platform.system()} {platform.machine()}"
    shell = os.environ.get("SHELL", "/bin/sh")
    return (
        f"# Environment\n"
        f"Working directory: {Path.cwd()}\n"
        f"Platform: {plat}\n"
        f"Shell: {shell}"
        f"{get_git_context()}{build_memory_prompt_section()}"
        f"{build_skill_descriptions()}{build_agent_descriptions()}"
    )

def build_static_system_prompt() -> str:
    # 静态核心：模板原样返回——这是被 cache_control 缓存的块
    return STATIC_CORE

def build_user_context_reminder() -> str:
    # CLAUDE.md + 日期：包成 <system-reminder>，由 agent 注入第一条 user 消息
    from datetime import date
    return (
        "<system-reminder>\n"
        f"{load_agent_md()}\n"
        f"# currentDate\nToday's date is {date.today().isoformat()}.\n"
        "</system-reminder>"
    )

def build_memory_prompt_section() -> str:
    return ""

def build_skill_descriptions() -> str:
    return ""

def build_agent_descriptions() -> str:
    return ""
    