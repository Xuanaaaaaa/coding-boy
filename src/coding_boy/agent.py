from .tools import execute_tool,get_tool_schemas
import json
from typing import Optional
from .prompt import build_dynamic_system_context, build_static_system_prompt, build_user_context_reminder

class coding_boy():
    def __init__(self,agent_name: str,
        client,
        messages_history: Optional[list] = None,
        tool_provider=None):
        self.agent_name = agent_name
        self.messages = messages_history or []
        if messages_history is None:
            self.messages.append(
                {
                    "role": "system",
                    "content": f"{build_static_system_prompt()}"
                }
            )
            self.messages.append(
                {
                    "role": "system",
                    "content": f"{build_dynamic_system_context()}"
                }
            )
        self.client = client
        self.tool_provider = tool_provider or get_tool_schemas
        self._is_new_session = messages_history is None

    def deal_with_tools(self, tool_use_parts:list[dict]):
        result = {}
        for chunk in tool_use_parts:
            index = chunk["index"]
            if index not in result:
                result[index] = {
                    "id": chunk["id"],
                    "type": chunk["type"],
                    "function": {
                        "name": chunk["function"]["name"],
                        "arguments": chunk["function"]["arguments"] or "",
                    },
                }
            else:
                arguments_part = chunk["function"]["arguments"] or ""
                result[index]["function"]["arguments"] += arguments_part
        return result

    def run_turn(self, new_message: str) -> str:
        turns = 0
        if self._is_new_session:
            self.messages.append({"role": "user", "content": f"{build_user_context_reminder()}\n\n{new_message}"})
        else:
            self.messages.append({"role": "user", "content": new_message})
        while turns < 10:
            turns += 1
            content_parts = []
            tool_use_parts = []
            tools_list = self.tool_provider()
            response = self.client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=self.messages,
                stream=True,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
                tools=tools_list
            )
            for chunk in response:
                content = chunk.choices[0].delta.content
                tool_use = chunk.choices[0].delta.tool_calls
                if content:
                    print(content, end="")
                    content_parts.append(content)
                if tool_use:
                    for part in tool_use or []:
                        tool_use_parts.append(part.model_dump())
            print("\n", end="")
            assistant_message = "".join(content_parts)
            tool_use_message = self.deal_with_tools(tool_use_parts)
            tool_calls = [
                tool_use_message[index]
                for index in sorted(tool_use_message)
            ]
            if not tool_calls:
                self.messages.append({"role": "assistant",
                    "content": assistant_message,
                })
                return assistant_message
            self.messages.append({"role": "assistant",
                "content": assistant_message,
                "tool_calls": tool_calls},
            )
            for tool_call in tool_calls:
                name = tool_call["function"]["name"]
                try:
                    args = json.loads(tool_call["function"]["arguments"])
                except Exception as e:
                    tool_result = f"参数解析发生错误，具体报错为：{e}"
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result
                        }
                    )
                    continue
                tool_result = execute_tool(name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result
                    }
                )
        error_message = "工具调用达到最大轮数，已停止继续执行"
        self.messages.append(
            {
                "role": "assistant",
                "content": error_message
            }
        )
        print(error_message)
        return error_message
