# SupportAgent/main.py
import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load environment early so llm_service picks up values on import
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from agents import ConversationAgent, OrchestratorAgent, SalesAgent, SupportAgent  # noqa: E402
from user_functions import user_functions  # set of callables


def _guess_route(user_msg: str) -> str:
    text = (user_msg or "").lower()
    support_terms = ("status", "issue", "problem", "ticket", "support", "repair", "broken", "warranty")
    sales_terms = ("buy", "purchase", "price", "order", "quote", "spec", "laptop")
    if any(term in text for term in support_terms):
        return "support"
    if any(term in text for term in sales_terms):
        return "sales"
    return "conversation"


def main():
    logging.basicConfig(level=logging.INFO)

    orch = OrchestratorAgent()
    sales = SalesAgent()
    sup = SupportAgent()
    convo = ConversationAgent()

    history = []
    current = orch

    print("System ready. Type 'quit' to exit.")
    print("Assistant: Hi! I can help with laptop purchases or support. What do you need?")
    while True:
        user = input("You: ").strip()
        if user.lower() == "quit":
            break
        history.append({"role": "user", "content": user})

        # 1) Orchestrator turn
        msg = asyncio.run(orch.chat_async(history))
        if msg.function_call:
            args = json.loads(msg.function_call.arguments)
            target = args.get("target")
        else:
            target = _guess_route(user)
            args = {"target": target, "auto_routed": True}

        print(f"Routing to {target.title()}")
        history.append({
            "role": "function",
            "name": "route_to_agent",
            "content": json.dumps(args)
        })
        if target == "sales":
            current = sales
        elif target == "support":
            current = sup
        else:
            current = convo

        # 2) Sub-agent turn
        msg2 = asyncio.run(current.chat_async(history))
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
