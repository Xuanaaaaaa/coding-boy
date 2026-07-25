"""
该注册模块实现的功能可以概括为：当我们把工具按照一定的规则实现以后（如类型注解清晰，解释说明字段完整等），通过装饰器，能够直接将该函数工具
的信息收集起来并组装成能够发送给大模型api的形式，这样就省去了每写一个工具都要手动写JSON Schmea的麻烦。

最终产出的就是一个工具信息列表，可以直接作为参数传给大模型api，以及一个工具映射表，方便大模型在发出工具调用请求以后能够直接匹配到要执行的
函数本身
"""

import inspect
import types
from collections.abc import Callable
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

TOOL_SCHEMAS: list[dict] = []
TOOL_FUNCTIONS: dict[str, Callable] = {}
_ACTIVATED_TOOLS: set[str] = set()

_TOOL_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "tool_search",
        "description": "搜索可用工具。当你需要某个功能但当前工具列表中没有时，用它按名称/关键词搜索并激活对应工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "工具名称或功能关键词，如 shell、web、search",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

_JSON_TYPES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    type(None): "null",
}


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)

    if origin is Annotated:
        base_type, *metadata = get_args(annotation)
        schema = _annotation_to_schema(base_type)
        description = next((item for item in metadata if isinstance(item, str)), None)
        if description is not None:
            schema["description"] = description
        return schema

    if origin is Literal:
        values = list(get_args(annotation))
        schema: dict[str, Any] = {"enum": values}
        json_types = list(dict.fromkeys(_JSON_TYPES.get(type(value)) for value in values))
        if None not in json_types:
            schema["type"] = json_types[0] if len(json_types) == 1 else json_types
        return schema

    if origin in (Union, types.UnionType):
        choices = [_annotation_to_schema(item) for item in get_args(annotation)]
        simple_types = [choice.get("type") for choice in choices]
        if all(
            set(choice) == {"type"} and isinstance(item, str)
            for choice, item in zip(choices, simple_types, strict=True)
        ):
            return {"type": simple_types}
        return {"anyOf": choices}

    if origin is list:
        item_types = get_args(annotation)
        if len(item_types) != 1:
            raise TypeError("list parameters must declare exactly one item type")
        return {
            "type": "array",
            "items": _annotation_to_schema(item_types[0]),
        }

    json_type = _JSON_TYPES.get(annotation)
    if json_type is not None:
        return {"type": json_type}

    raise TypeError(f"unsupported tool parameter annotation: {annotation!r}")

# 产出单个工具的JSON Schema
def build_tool_schema(
    function: Callable[..., Any],
) -> dict[str, Any]:
    signature = inspect.signature(function)
    type_hints = get_type_hints(function, include_extras=True)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, parameter in signature.parameters.items():
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise TypeError(
                f"tool parameter {name!r} must be positional-or-keyword or keyword-only"
            )

        if name not in type_hints:
            raise TypeError(f"tool parameter {name!r} is missing a type annotation")

        properties[name] = _annotation_to_schema(type_hints[name])
        if parameter.default is inspect.Parameter.empty:
            required.append(name)

    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        parameters["required"] = required

    return {
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": inspect.getdoc(function) or "",
            "parameters": parameters,
        },
    }
# 实现工具注册的装饰器
def tool(function=None, *, deferred=False):
    def decorator(function):
        tool_schema = build_tool_schema(function)
        tool_schema["deferred"] = deferred
        if tool_schema["function"]["name"] not in [tool["function"]["name"] for tool in TOOL_SCHEMAS]:
            TOOL_SCHEMAS.append(tool_schema)
            TOOL_FUNCTIONS[tool_schema["function"]["name"]] = function
        else:
            raise Exception("工具列表存在冲突")
        return function
    if function is not None:
        return decorator(function)
    return decorator



