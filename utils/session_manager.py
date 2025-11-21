"""
Session manager for SupportAgent.
Maintains per-session histories and metadata using the SessionState model.
"""

import logging
from typing import Dict

from models import SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
            logger.info("Created new session state: %s", session_id)
        return self._sessions[session_id]

    def upsert_history(self, session_id: str, history, *, summary=None, slots=None, last_agent=None):
        state = self.get(session_id)
        state.history = history
        if summary is not None:
            state.summary = summary
        if slots:
            state.slots.update(slots)
        if last_agent:
            state.last_agent = last_agent
        state._touch()
        self._sessions[session_id] = state
        return state

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self._sessions)


session_manager = SessionManager()
