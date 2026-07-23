import unittest
from typing import Annotated, Literal

from tools.registry import tool_register


class ToolRegisterTests(unittest.TestCase):
    def test_builds_schema_from_signature_and_annotations(self) -> None:
        def read_file(
            path: Annotated[str, "需要读取的文件路径"],
            line_numbers: list[int] | None = None,
            mode: Literal["text", "binary"] = "text",
        ) -> str:
            """读取指定文件。"""
            return path

        schema = tool_register(read_file)

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

    def test_rejects_missing_parameter_annotation(self) -> None:
        def missing_annotation(path):
            return path

        with self.assertRaisesRegex(TypeError, "missing a type annotation"):
            tool_register(missing_annotation)

    def test_rejects_variadic_parameters(self) -> None:
        def variadic(*paths: str) -> str:
            return "".join(paths)

        with self.assertRaisesRegex(TypeError, "positional-or-keyword or keyword-only"):
            tool_register(variadic)


if __name__ == "__main__":
    unittest.main()
