import time
import json
from pathlib import Path

MAX_RESULT_CHARS = 50000
MAX_RESULT_BYTES = 30 * 1024  # 30 KB
PREVIEW_LINES = 200
TOOL_RESULT_DIR = Path.home() / ".coding-boy" / "tool-results"
SNIPPABLE_TOOLS = { "grep_search", "list_files"}
SNIP_PLACEHOLDER = "[Content snipped - re-read if needed]"
KEEP_RECENT_RESULTS = 3
MICROCOMPACT_IDLE_S = 5 * 60

# 直接对超过长度上限的工具结果进行裁剪
def truncate_result(result: str) -> str:
    if len(result) <= MAX_RESULT_CHARS:
        return result
    keep_each = (MAX_RESULT_CHARS - 60) // 2
    return (
        result[:keep_each]
        + f"\n\n[... truncated {len(result) - keep_each * 2} chars ...]\n\n"
        + result[-keep_each:]
    )


def persist_large_result(tool_name: str, result: str) -> str:
    """大工具结果落盘：上下文只留预览 + 文件指针，模型可按需 read_file 取全文"""
    size_bytes = len(result.encode("utf-8"))
    if size_bytes <= MAX_RESULT_BYTES:
        return result

    TOOL_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{int(time.time() * 1000)}-{tool_name}.txt"
    filepath = TOOL_RESULT_DIR / filename
    filepath.write_text(result, encoding="utf-8")

    lines = result.split("\n")
    preview = "\n".join(lines[:PREVIEW_LINES])
    size_kb = size_bytes / 1024

    return (
        f"[Result too large ({size_kb:.1f} KB, {len(lines)} lines). "
        f"Full output saved to {filepath}. "
        f"You can use read_file to see the full result if necessary.]\n\n"
        f"Preview (first {PREVIEW_LINES} lines):\n{preview}"
    )

def budget_tool_results(messages: list, last_input_token_count: int, effective_window: int) -> None:
    utilization = last_input_token_count / effective_window if effective_window else 0
    if utilization < 0.5:
        return
    budget = 15000 if utilization > 0.70 else 30000
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if not isinstance(content, str) or len(content) <= budget:
            continue
        keep = (budget - 80) // 2
        msg["content"] = (
            content[:keep]
            + f"\n\n[... budgeted: {len(content) - keep * 2} chars truncated ...]\n\n"
            + content[-keep:]
        )

def build_call_map(messages: list) -> dict:
    """tool_call_id -> (工具名, read_file 的 path)，从 assistant 消息解析"""
    call_map = {}
    for msg in messages:
        if msg.get("role") != "assistant" or not msg.get("tool_calls"):
            continue
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            path = None
            if name == "read_file":
                try:
                    path = json.loads(tc["function"]["arguments"]).get("path")
                except Exception:
                    pass
            call_map[tc["id"]] = (name, path)
    return call_map

def snip_tool_results(last_input_token_count: int, effective_window: int, messages: list) -> None:
    utilization = last_input_token_count / effective_window if effective_window else 0
    if utilization < 0.60:
        return

    call_map = build_call_map(messages)
    tool_indexes = [i for i, m in enumerate(messages) if m.get("role") == "tool"]

    # 规则 3：最近 3 个 tool 结果永远保留
    keep = set(tool_indexes[-KEEP_RECENT_RESULTS:])
    to_snip: set[int] = set()

    # 规则 1：同一文件被 read_file 多次 → 只留最新一次
    by_path: dict = {}
    for i in tool_indexes:
        name, path = call_map.get(messages[i].get("tool_call_id"), (None, None))
        if name == "read_file" and path:
            by_path.setdefault(path, []).append(i)
    for idxs in by_path.values():
        for i in idxs[:-1]:                      # 最旧的全部 snip
            if i not in keep:
                to_snip.add(i)

    # 规则 2：同类工具结果超过 KEEP_RECENT_RESULTS 个 → snip 最旧的
    by_name: dict = {}
    for i in tool_indexes:
        name, _ = call_map.get(messages[i].get("tool_call_id"), (None, None))
        if name in SNIPPABLE_TOOLS:
            by_name.setdefault(name, []).append(i)
    for idxs in by_name.values():
        if len(idxs) > KEEP_RECENT_RESULTS:
            for i in idxs[:len(idxs) - KEEP_RECENT_RESULTS]:
                if i not in keep:
                    to_snip.add(i)

    # 应用：只清 content，不动 tool_call_id / assistant 的 tool_calls
    for i in to_snip:
        messages[i]["content"] = SNIP_PLACEHOLDER

def microcompact_tool_results(messages: list, last_api_call_time: float,
                              idle_s: int = MICROCOMPACT_IDLE_S) -> None:
    """闲置超过 idle_s 秒后，清除除最近 KEEP_RECENT_RESULTS 个外的所有 tool_result。
    时间维度的回收，与 budget / snip（空间维度）互补。"""
    if not last_api_call_time:
        return
    if time.time() - last_api_call_time < idle_s:
        return

    tool_indexes = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    keep = set(tool_indexes[-KEEP_RECENT_RESULTS:])
    for i in tool_indexes:
        if i not in keep and messages[i].get("content") != SNIP_PLACEHOLDER:
            messages[i]["content"] = "[Old result cleared]"
