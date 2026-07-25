from .registry import TOOL_SCHEMAS, _TOOL_SEARCH_SCHEMA, TOOL_FUNCTIONS, _ACTIVATED_TOOLS
import inspect
from typing import Any

# 对外暴露的接口，用于获取工具列表
def get_tool_schemas():
    # 非延迟工具 + 已激活的延迟工具
    active = [
            t for t in TOOL_SCHEMAS
            if not t.get("deferred") or t["function"]["name"] in _ACTIVATED_TOOLS
        ]
     # 去掉 deferred 字段，再追加 tool_search
    return [
        {k: v for k, v in t.items() if k != "deferred"}
        for t in active
    ] + [_TOOL_SEARCH_SCHEMA]

def _execute_tool_search(args: dict) -> str:
    query = args["query"].lower()
    deferred = [t for t in TOOL_SCHEMAS if t.get("deferred")]
    matches = [
        t for t in deferred
        if query in t["function"]["name"].lower()
        or query in t["function"]["description"].lower()
    ]
    if not matches:
        return f"未找到匹配 '{args['query']}' 的工具。可用的延迟工具有: {', '.join(t['function']['name'] for t in deferred)}"
    for m in matches:
        _ACTIVATED_TOOLS.add(m["function"]["name"])
    names = [t["function"]["name"] for t in matches]
    return f"已加载新的工具：{', '.join(names)}"



# 统一的工具执行函数
def execute_tool(name: str, args: dict[str, Any],) -> str:
    if name == "tool_search":
        return _execute_tool_search(args)
    try:
        try:
            function = TOOL_FUNCTIONS[name]
        except KeyError:
            return "未知工具"
        signature = inspect.signature(function)
        try:
            signature.bind(**args) # 调用真实函数前先检查传回的参数类型是否正确
        except TypeError:
            return "调用参数不正确"
        print(f"正在尝试调用工具：{name}")
        result = function(**args)     
    except Exception as e:
        return f"工具调用失败：{e}"
    return result
