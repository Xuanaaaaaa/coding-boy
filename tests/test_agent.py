import io
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from coding_boy.agent import coding_boy


class FakeToolCallPart:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def model_dump(self) -> dict:
        return self.payload


def make_chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta)
    return SimpleNamespace(choices=[choice])


def make_tool_part(
    *,
    index: int = 0,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str = "",
) -> FakeToolCallPart:
    return FakeToolCallPart(
        {
            "index": index,
            "id": call_id,
            "type": "function" if call_id is not None else None,
            "function": {
                "name": name,
                "arguments": arguments,
            },
        }
    )


class FakeCompletions:
    def __init__(self, responses: list[list]) -> None:
        self.responses = iter(responses)
        self.call_count = 0
        self.requests = []

    def create(self, **kwargs):
        self.call_count += 1
        self.requests.append(deepcopy(kwargs))
        return iter(next(self.responses))


def make_agent(responses: list[list]):
    completions = FakeCompletions(responses)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )
    messages = []
    agent = coding_boy(
        agent_name="test-agent",
        tools_list=[],
        messages_history=messages,
        client=client,
    )
    return agent, messages, completions


class AgentRunTurnTests(unittest.TestCase):
    def test_returns_final_response_without_tool_calls(self) -> None:
        agent, messages, completions = make_agent(
            [[make_chunk(content="final answer")]]
        )

        with redirect_stdout(io.StringIO()):
            result = agent.run_turn("hello")

        self.assertEqual(result, "final answer")
        self.assertEqual(completions.call_count, 1)
        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "final answer"},
            ],
        )

    @patch("coding_boy.agent.execute_tool", return_value="tool result")
    def test_aggregates_tool_arguments_and_requests_follow_up(
        self,
        execute_tool,
    ) -> None:
        first_part = make_tool_part(
            call_id="call_1",
            name="demo",
            arguments='{"value":',
        )
        second_part = make_tool_part(arguments="1}")
        agent, messages, completions = make_agent(
            [
                [
                    make_chunk(tool_calls=[first_part]),
                    make_chunk(tool_calls=[second_part]),
                ],
                [
                    make_chunk(content="final "),
                    make_chunk(content="answer"),
                ],
            ]
        )

        with redirect_stdout(io.StringIO()):
            result = agent.run_turn("use a tool")

        self.assertEqual(result, "final answer")
        self.assertEqual(completions.call_count, 2)
        execute_tool.assert_called_once_with("demo", {"value": 1})
        self.assertEqual(
            [message["role"] for message in messages],
            ["user", "assistant", "tool", "assistant"],
        )
        self.assertEqual(
            messages[1]["tool_calls"][0]["function"]["arguments"],
            '{"value":1}',
        )
        self.assertEqual(
            messages[2],
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": "tool result",
            },
        )
        second_request_messages = completions.requests[1]["messages"]
        self.assertEqual(
            [message["role"] for message in second_request_messages],
            ["user", "assistant", "tool"],
        )
        self.assertEqual(
            second_request_messages[-1],
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": "tool result",
            },
        )

    @patch("coding_boy.agent.execute_tool")
    def test_records_invalid_json_as_tool_result(
        self,
        execute_tool,
    ) -> None:
        invalid_part = make_tool_part(
            call_id="call_bad",
            name="demo",
            arguments="{",
        )
        agent, messages, completions = make_agent(
            [
                [make_chunk(tool_calls=[invalid_part])],
                [make_chunk(content="recovered")],
            ]
        )

        with redirect_stdout(io.StringIO()):
            result = agent.run_turn("bad arguments")

        self.assertEqual(result, "recovered")
        self.assertEqual(completions.call_count, 2)
        execute_tool.assert_not_called()
        self.assertEqual(
            [message["role"] for message in messages],
            ["user", "assistant", "tool", "assistant"],
        )
        self.assertEqual(messages[2]["tool_call_id"], "call_bad")
        self.assertIn("参数解析发生错误", messages[2]["content"])

    @patch("coding_boy.agent.execute_tool", return_value="tool result")
    def test_stops_after_ten_tool_rounds(self, execute_tool) -> None:
        responses = [
            [
                make_chunk(
                    tool_calls=[
                        make_tool_part(
                            call_id=f"call_{index}",
                            name="demo",
                            arguments="{}",
                        )
                    ]
                )
            ]
            for index in range(10)
        ]
        agent, messages, completions = make_agent(responses)

        with redirect_stdout(io.StringIO()):
            result = agent.run_turn("keep calling tools")

        self.assertEqual(result, "工具调用达到最大轮数，已停止继续执行")
        self.assertEqual(completions.call_count, 10)
        self.assertEqual(execute_tool.call_count, 10)
        self.assertEqual(
            messages[-1],
            {
                "role": "assistant",
                "content": "工具调用达到最大轮数，已停止继续执行",
            },
        )


if __name__ == "__main__":
    unittest.main()
