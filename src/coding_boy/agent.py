from .tools import execute_tool,get_tool_schemas
import json
from .prompt import build_dynamic_system_context, build_static_system_prompt, build_user_context_reminder
from .session import generate_session_id, load_session, save_session
from .retry import with_retry
from .ui import print_retry

class coding_boy():
    def __init__(self,agent_name: str,
        client,
        session_id: str | None = None,
        tool_provider=None):
        self.agent_name = agent_name
        self.session_id = session_id or generate_session_id()
        self.client = client
        self.messages: list[dict] = []
        if session_id:
            # 恢复会话
            loaded_messages = load_session(session_id)
            if loaded_messages is None:
                # 会话文件不存在，当作新会话处理
                self.session_id = generate_session_id()
                self._init_new_session()
            else:
                self.messages = loaded_messages
                self._is_new_session = False
        else:
            self._init_new_session()
        self.tool_provider = tool_provider or get_tool_schemas

    def _init_new_session(self):
        """初始化新会话"""
        self.messages = []
        self.messages.append({"role": "system", "content": build_static_system_prompt()})
        self.messages.append({"role": "system", "content": build_dynamic_system_context()})
        self._is_new_session = True

    def _auto_save(self):
        try:
            save_session(self.session_id, self.messages)
        except Exception:
            pass
    
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

    def _call_llm(self):
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
        return content_parts, tool_use_parts

    def run_turn(self, new_message: str) -> str:
        turns = 0
        if self._is_new_session:
            self.messages.append({"role": "user", "content": f"{build_user_context_reminder()}\n\n{new_message}"})
            self._is_new_session = False
        else:
            self.messages.append({"role": "user", "content": new_message})
        while turns < 10:
            turns += 1
            content_parts, tool_use_parts = with_retry(
                lambda: self._call_llm(),
                max_retries=3,
                on_retry=lambda n, total, reason: print_retry,
            )
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
                self._auto_save()
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
        self._auto_save()
        print(error_message)
        return error_message
