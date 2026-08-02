import argparse
from .ui import print_welcome, select_permission_mode, print_error, print_info
from .session import generate_session_id

SENTINEL = "[已完成对话压缩，上下文见上方总结。]"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="coding-boy", add_help=False)
    parser.add_argument("prompt", nargs="*")
    parser.add_argument("--yolo", "-y", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--accept-edits", action="store_true")
    parser.add_argument("--dont-ask", action="store_true")
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--model", "-m", default=None)
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-cost", type=float, default=None)
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()

def _resolve_permission_mode(args: argparse.Namespace) -> str:
    if args.yolo:
        return "bypassPermissions"
    if args.plan:
        return "plan"
    if args.accept_edits:
        return "acceptEdits"
    if args.dont_ask:
        return "dontAsk"
    return "default"


def chat_loop(agent):
    print_welcome()
    while True:
        try:
            user_message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!\n")
            break
        if user_message == "quit" or user_message == "exit":
            print("\nBye!\n")
            break
        if user_message == "":
            continue
        if user_message == "/clear":
            agent.messages = []
            agent.session_id = generate_session_id()
            agent._init_new_session()
            print("History cleared. New session started.")
            continue
        if user_message == "/mode":
            new_mode = select_permission_mode()
            agent.permission_mode = new_mode
            print_info(f"Switched to {new_mode} mode")
            continue
        if user_message == "/compact":
            agent.messages.append({"role": "assistant", "content": SENTINEL})
            compacted = agent.compact_conversation()
            if agent.messages and agent.messages[-1].get("content") == SENTINEL:
                agent.messages.pop()
            if compacted:
                print_info("Conversation compacted")
            continue
        try:
            agent.run_turn(user_message)
        except Exception as e:
            print_error(str(e))