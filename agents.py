# SupportAgent/agents.py
import json
import openai
import logging

class BaseAgent:
    def __init__(self, *, name: str, instruction: str, functions: list, deployment: str):
        self.name        = name
        self.instruction = instruction
        self.functions   = functions
        self.deployment  = deployment
        self.logger      = logging.getLogger(name)

    def chat(self, messages, function_call="auto"):
        # Ensure our system prompt is at the front
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.instruction}] + messages

        # NEW v1 API call:
        resp = openai.chat.completions.create(
            model=self.deployment,        # 'model' not 'engine'
            messages=messages,
            functions=self.functions,
            function_call=function_call
        )
        # Log the response content for debugging
        self.logger.info(f"Response content: {resp.choices[0].message.content}")
        return resp.choices[0].message

class OrchestratorAgent(BaseAgent):
    def __init__(self, deployment):
        instr = (
            "You are the orchestrator. Do NOT respond to the user directly. "
            "Based on the last user message, ALWAYS call "
            "`route_to_agent` with target 'sales' or 'support'."
        )
        fn = [{
            "name": "route_to_agent",
            "description": "Decide where to route the conversation",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "enum": ["sales", "support"]}
                },
                "required": ["target"]
            }
        }]
        super().__init__(name="orchestrator", instruction=instr, functions=fn, deployment=deployment)

class SalesAgent(BaseAgent):
    def __init__(self, deployment):
        instr = (
            "You are the sales agent. Handle ALL product and purchase inquiries. "
            "Ask clarifying questions (category, model preference, budget) and then gather "
            "name, email_address, product, quantity. Use get_laptops_in_category, "
            "get_laptop_details, or process_sales_order to fulfill the request. "
            "Only route to support via route_to_agent(target:'support') if the user explicitly asks for technical help. "
            "Never tell the user you are transferring them; just proceed with sales assistance."
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
        super().__init__(name="sales", instruction=instr, functions=fn, deployment=deployment)

class SupportAgent(BaseAgent):
    def __init__(self, deployment):
        instr = (
            "You are the support agent. Handle all support and status inquiries. "
            "Gather email_address, order_number, and a description, then call submit_support_ticket. "
            "Provide status updates by acknowledging the ticket/order and asking for missing details. "
            "Only route to sales via route_to_agent(target:'sales') if the user explicitly wants to buy something. "
            'Do not say you are transferring; simply ask the needed support questions.'
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
        super().__init__(name="support", instruction=instr, functions=fn, deployment=deployment)
