from agents.base_agent import BaseAgent


class SalesAgent(BaseAgent):
    def __init__(self):
        instr = (
            "You are the sales agent. Handle ALL product inquiries. "
            "Gather category, model, budget, then name, email_address, product, quantity. "
            "Use catalog functions to suggest, compare, and place orders. "
            "If budget is too low for options, say so politely and suggest closest matches. "
            "Only route to support if the user explicitly wants technical help. "
            "Never say you are transferring; just help with sales."
        )
        fn = [
            {
                "name": "get_laptops_in_category",
                "description": "Fetch laptops in a category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"}
                    },
                    "required": ["category"]
                }
            },
            {
                "name": "get_laptop_details",
                "description": "Fetch specs and price for a model",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"}
                    },
                    "required": ["model"]
                }
            },
            {
                "name": "process_sales_order",
                "description": "Create a sales order",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email_address": {"type": "string"},
                        "product": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["name", "email_address", "product", "quantity"]
                }
            },
            {
                "name": "get_order_status",
                "description": "Get the status of an order",
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
            name="sales",
            prompt_key="sales",
            fallback_prompt=instr,
            functions=fn,
        )
