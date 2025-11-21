from agents.base_agent import BaseAgent


class SupportAgent(BaseAgent):
    def __init__(self):
        instr = (
            "You are the support agent. Handle issues, troubleshooting, and status. "
            "Gather email_address, order_number, description; submit support tickets and check statuses. "
            "Identify issue category and severity; offer brief triage if obvious. "
            "Only route to sales if the user explicitly wants to buy. "
            "Never say you are transferring; stay concise on next steps."
        )
        fn = [
            {
                "name": "submit_support_ticket",
                "description": "Create a support ticket",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_address": {"type": "string"},
                        "order_number":  {"type": "string"},
                        "description":   {"type": "string"}
                    },
                    "required": ["email_address", "order_number", "description"]
                }
            },
            {
                "name": "get_ticket_status",
                "description": "Get status of a ticket",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string"}
                    },
                    "required": ["ticket_id"]
                }
            },
            {
                "name": "get_order_status",
                "description": "Get status of an order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"}
                    },
                    "required": ["order_id"]
                }
            },
            {
                "name": "route_to_agent",
                "description": "Route to another agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"}
                    },
                    "required": ["target"]
                }
            }
        ]
        super().__init__(
            name="support",
            prompt_key="support",
            fallback_prompt=instr,
            functions=fn,
        )
