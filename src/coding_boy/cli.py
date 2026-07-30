import argparse
from .ui import print_welcome
from .session import generate_session_id
from .ui import print_error

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
        try:
            agent.run_turn(user_message)
        except Exception as e:
            print_error(str(e))