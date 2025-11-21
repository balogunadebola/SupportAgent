from agents.base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    def __init__(self):
        instr = (
            "You are the orchestrator. Do NOT respond to the user directly. "
            "Based on the last user message, ALWAYS call "
            "`route_to_agent` with target 'sales', 'support', or 'conversation'."
        )
        fn = [{
            "name": "route_to_agent",
            "description": "Decide where to route the conversation",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "enum": ["sales", "support", "conversation"]}
                },
                "required": ["target"]
            }
        }]
        super().__init__(
            name="orchestrator",
            prompt_key="orchestrator",
            fallback_prompt=instr,
            functions=fn,
        )
