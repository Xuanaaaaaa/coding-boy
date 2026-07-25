import unittest
from typing import Annotated, Literal

from coding_boy.tools import get_tool_schemas
from coding_boy.tools.registry import build_tool_schema


class ToolRegistryTests(unittest.TestCase):
    def test_builds_schema_from_signature_and_annotations(self) -> None:
        def read_file(
            path: Annotated[str, "需要读取的文件路径"],
            line_numbers: list[int] | None = None,
            mode: Literal["text", "binary"] = "text",
        ) -> str:
            """读取指定文件。"""
            return path

        schema = build_tool_schema(read_file)

        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "read_file")
        self.assertEqual(schema["function"]["description"], "读取指定文件。")
        self.assertEqual(
            schema["function"]["parameters"],
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "需要读取的文件路径",
                    },
                    "line_numbers": {
                        "anyOf": [
                            {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                            {"type": "null"},
                        ]
                    },
                    "mode": {
                        "enum": ["text", "binary"],
                        "type": "string",
                    },
                },
                "additionalProperties": False,
                "required": ["path"],
            },
        )

    def test_package_entry_loads_read_file_once(self) -> None:
        names = [
            schema["function"]["name"]
            for schema in get_tool_schemas()
        ]

        self.assertEqual(names.count("read_file"), 1)

    def test_returned_schema_list_is_a_copy(self) -> None:
        schemas = get_tool_schemas()
        schemas.clear()

        names = [
            schema["function"]["name"]
            for schema in get_tool_schemas()
        ]
        self.assertIn("read_file", names)

    def test_rejects_missing_parameter_annotation(self) -> None:
        def missing_annotation(path):
            return path

        with self.assertRaisesRegex(TypeError, "missing a type annotation"):
            build_tool_schema(missing_annotation)

    def test_rejects_variadic_parameters(self) -> None:
        def variadic(*paths: str) -> str:
            return "".join(paths)

        with self.assertRaisesRegex(TypeError, "positional-or-keyword or keyword-only"):
            build_tool_schema(variadic)


if __name__ == "__main__":
    unittest.main()
