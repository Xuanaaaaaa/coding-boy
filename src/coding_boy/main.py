import os
from dotenv import load_dotenv
from openai import OpenAI
from .cli import chat_loop
from .agent import coding_boy

load_dotenv()

def main():
    messages = []
    client = OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("BASE_URL")
    )
    agent = coding_boy("master", messages, client)
    chat_loop(agent)
if __name__ == "__main__":
    main()
