import inspect
import types
from collections.abc import Callable
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints


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


def tool_register(
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
