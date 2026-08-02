from .tools import execute_tool,get_tool_schemas
import json
import time
from .prompt import build_dynamic_system_context, build_static_system_prompt, build_user_context_reminder
from .session import generate_session_id, load_session, save_session
from .retry import with_retry
from .ui import print_retry
from .permission import PermissionManager
from .ui import print_info, print_confirmation
from .context import persist_large_result, snip_tool_results, truncate_result, budget_tool_results, microcompact_tool_results

class coding_boy():
    def __init__(self,agent_name: str,
        client,
        session_id: str | None = None,
        tool_provider=None,
        permission_mode: str = "default",
        _plan_file_path: str | None = None,
    ):
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
        self.permission_mode = permission_mode
        self._plan_file_path = _plan_file_path
        self._confirmed_paths: set[str] = set()
        self.last_input_token_count = 0
        self.effective_window = 128_000
        self.last_api_call_time = 0.0

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
        self.last_api_call_time = time.time()
        response = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=self.messages,
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
            tools=tools_list,
            stream_options={"include_usage": True},
        )
        for chunk in response:
            if chunk.usage:
                self.last_input_token_count = chunk.usage.prompt_tokens
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            tool_use = chunk.choices[0].delta.tool_calls
            if content:
                print(content, end="")
                content_parts.append(content)
            if tool_use:
                for part in tool_use or []:
                    tool_use_parts.append(part.model_dump())
        return content_parts, tool_use_parts
        
    def _confirm_dangerous(self, command: str) -> bool:
        """确认危险操作"""
        print_confirmation(command)
        try:
            answer = input("  Allow? (y/n): ")
            return answer.lower().startswith("y")
        except EOFError:
            return False

    def check_and_compact(self) -> None:
        if self.last_input_token_count > self.effective_window * 0.85:
            print_info("Context window filling up, compacting conversation...")
            if self.compact_conversation():
                print_info("Conversation compacted")

    def compact_conversation(self) -> bool:
        if len(self.messages) < 5:
            print_info("对话过短，无需压缩")
            return False
        last_user_msg = self.messages[-1]
        system_count = sum(1 for m in self.messages if m.get("role") == "system")
        try:
            self.last_api_call_time = time.time()
            summary_resp = self.client.chat.completions.create(
                model="deepseek-v4-flash",
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": "You are a conversation summarizer. Be concise but preserve important details."},
                    *self.messages[system_count:-1],
                    {"role": "user", "content": "总结到目前为止的对话内容..."},
                ],
            )
        except Exception as e:
            print_info(f"压缩失败: {e}")
            return False
        summary_text = summary_resp.choices[0].message.content or "没有可用的总结."
        self._init_new_session()
        self.messages.append({"role": "user", "content": f"[Previous conversation summary]\n{summary_text}"})
        self.messages.append({"role": "assistant", "content": "了解，我现在知道了对话总结的结果."})

        if last_user_msg.get("role") == "user":
            self.messages.append(last_user_msg)
        self.last_input_token_count = 0
        return True

    
    def run_turn(self, new_message: str) -> str:
        turns = 0
        if self._is_new_session:
            self.messages.append({"role": "user", "content": f"{build_user_context_reminder()}\n\n{new_message}"})
            self._is_new_session = False
        else:
            self.messages.append({"role": "user", "content": new_message})
        self.check_and_compact()
        while turns < 10:
            turns += 1
            microcompact_tool_results(self.messages, self.last_api_call_time)
            budget_tool_results(self.messages, self.last_input_token_count, self.effective_window)
            snip_tool_results(self.last_input_token_count, self.effective_window, self.messages)
            content_parts, tool_use_parts = with_retry(
                lambda: self._call_llm(),
                max_retries=3,
                on_retry=print_retry,
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
                perm = PermissionManager.check_permission(name, args, self.permission_mode, self._plan_file_path)
                if perm["action"] == "deny":
                    print_info(f"Denied: {perm.get('message', '')}")
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": f"Action denied: {perm.get('message', '')}"
                    })
                    continue
                if perm["action"] == "confirm" and perm.get("message") and perm["message"] not in self._confirmed_paths:
                    confirmed = self._confirm_dangerous(perm["message"])
                    if not confirmed:
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": "User denied this action."
                        })
                        continue
                    self._confirmed_paths.add(perm["message"])
                tool_result = execute_tool(name, args)
                tool_result = persist_large_result(name, tool_result)
                tool_result = truncate_result(tool_result)
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
        