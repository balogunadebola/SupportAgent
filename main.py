# SupportAgent/main.py

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import openai

from agents import OrchestratorAgent, SalesAgent, SupportAgent
from user_functions import user_functions  # set of callables

def setup_openai():
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    openai.api_type    = "azure"
    openai.api_base    = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai.api_key     = os.getenv("AZURE_OPENAI_API_KEY")
    openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

def main():
    logging.basicConfig(level=logging.INFO)
    deployment = setup_openai()

    orch  = OrchestratorAgent(deployment)
    sales = SalesAgent(deployment)
    sup   = SupportAgent(deployment)

    history = []
    current = orch

    print("🛠️ System ready. Type 'quit' to exit.")
    while True:
        user = input("You: ").strip()
        if user.lower() == "quit":
            break
        history.append({"role": "user", "content": user})

        # 1) Orchestrator turn
        msg = orch.chat(history)
        if msg.function_call:
            args = json.loads(msg.function_call.arguments)
            target = args["target"]
            print(f"↪ Routing to {target.title()}…")
            history.append({
                "role": "function",
                "name": "route_to_agent",
                "content": json.dumps(args)
            })
            current = sales if target == "sales" else sup
        else:
            # If no function call is required, let the model handle the response directly
            print(f"Assistant: {msg.content}")
            history.append({"role": "assistant", "content": msg.content})
            continue

        # 2) Sub-agent turn
        msg2 = current.chat(history)
        if msg2.function_call:
            fname = msg2.function_call.name
            fargs = json.loads(msg2.function_call.arguments)
            # call the Python function
            result = {
                fn.__name__: fn for fn in user_functions
            }[fname](**fargs)
            history.append({
                "role": "function",
                "name": fname,
                "content": result
            })
            # Extract user_reply from the function result if available
            result_data = json.loads(result)
            user_reply = result_data.get("user_reply", "An error occurred while processing your request.")
            history.append({
                "role": "assistant",
                "content": user_reply
            })
            print(f"{current.name}: {user_reply}")
        else:
            print(f"{current.name}: {msg2.content}")
            history.append({"role": "assistant", "content": msg2.content})

if __name__ == "__main__":
    main()
