class coding_boy():
    def __init__(self,agent_name: str, tools_list: list, messages_history: list, client):
        self.agent_name = agent_name
        self.tools_list = tools_list
        self.messages = messages_history
        self.client = client
    def run_turn(self, new_message: str) -> str:
        parts = []
        self.messages.append({"role": "user", "content": new_message})
        response = self.client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=self.messages,
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
            tools=self.tools_list
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if not content:
                continue
            print(content, end="")
            parts.append(content)
        print("\n", end="")
        assistant_message = "".join(parts)
        self.messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message
