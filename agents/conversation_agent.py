from agents.base_agent import BaseAgent


class ConversationAgent(BaseAgent):
    def __init__(self):
        instr = (
            "You handle general conversation but only about laptop sales or support for orders/tickets. "
            "If the user goes off-topic, remind them politely that you can only help with purchases or support."
        )
        super().__init__(
            name="conversation",
            prompt_key="conversation",
            fallback_prompt=instr,
            functions=[],
        )
