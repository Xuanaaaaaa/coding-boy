import os
from dotenv import load_dotenv
from openai import OpenAI
from .cli import chat_loop, parse_args, _resolve_permission_mode
from .agent import coding_boy
import sys
from .session import get_latest_session_id 

load_dotenv()

def main():
    args = parse_args()
    # 处理 --help
    if args.help:
        print("usage: coding-boy [options] [prompt]")
        print("\nOptions:")
        print("  --yolo, -y        Bypass all permission checks")
        print("  --plan            Plan mode")
        print("  --accept-edits    all edits accepted")
        print("  --dont-ask        auto deny confirm request")
        print("  --model, -m       Model to use")
        print("  --api-base        API base URL")
        print("  --resume          Resume latest session")
        print("  --help, -h        Show this help message")
        return
    if args.api_base:
        api_key=os.getenv("API_KEY")
        base_url=args.api_base
    else:
        api_key=os.getenv("API_KEY")
        base_url=os.getenv("BASE_URL")
    if not api_key:
        print("API key is required.")
        sys.exit(1)
    client = OpenAI(
        api_key = api_key,
        base_url = base_url
    )
    permission_mode = _resolve_permission_mode(args)
    if args.resume:
        session_id = get_latest_session_id()
        if session_id:
            agent = coding_boy("master", client, session_id=session_id, permission_mode=permission_mode)
        else:
            print("No session to resume")
            agent = coding_boy("master", client, permission_mode=permission_mode)  # 新建会话
    else:
        agent = coding_boy("master", client, permission_mode=permission_mode)
    
    if args.prompt:
        prompt = " ".join(args.prompt)
        agent.run_turn(prompt)
    else:
        chat_loop(agent)

if __name__ == "__main__":
    main()