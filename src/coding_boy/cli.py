def chat_loop(agent):
    while True:
        user_message = input("> ")
        user_message = user_message.strip()
        if user_message == "bye":
            break
        if user_message == "":
            continue
        agent.run_turn(user_message)
