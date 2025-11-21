"""
Shared models for SupportAgent.
Includes API request/response schemas and a lightweight session state model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Chat schemas -----------------------------------------------------------------


class MessageDict(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client session identifier")
    message: str = Field(..., description="User message content")
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation turns, role/content pairs",
    )


class ChatResponse(BaseModel):
    reply: str
    updated_history: List[Dict[str, str]]
    used_agent: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    latency_ms: float
    fallback_used: bool


# Ticket schemas ---------------------------------------------------------------


class TicketMetaModel(BaseModel):
    ticket_id: str
    status: str
    created_at: Optional[str] = None
    summary: str


class TicketDetailsModel(TicketMetaModel):
    content: str


class TicketsListResponse(BaseModel):
    tickets: List[TicketMetaModel]


class TicketDetailsResponse(BaseModel):
    ticket: TicketDetailsModel


class TicketStatusUpdateRequest(BaseModel):
    status: str


class TicketStatusUpdateResponse(BaseModel):
    success: bool
    ticket_id: str
    new_status: str
    message: str


# Order schemas ----------------------------------------------------------------


class OrderMetaModel(BaseModel):
    order_id: str
    status: str
    created_at: Optional[str] = None
    summary: str


class OrderDetailsModel(OrderMetaModel):
    content: str


class OrdersListResponse(BaseModel):
    orders: List[OrderMetaModel]


class OrderDetailsResponse(BaseModel):
    order: OrderDetailsModel


class OrderStatusUpdateRequest(BaseModel):
    status: str


class OrderStatusUpdateResponse(BaseModel):
    success: bool
    order_id: str
    new_status: str
    message: str


# Session state ---------------------------------------------------------------


class SessionState(BaseModel):
    """
    Session state holder for chat history, slots, and summary.
    Enables richer context management without passing raw history from the client.
    """

    session_id: str
    history: List[Dict[str, str]] = Field(default_factory=list)
    last_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    slots: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_user(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._touch()

    def add_assistant(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._touch()

    def _touch(self):
        self.updated_at = datetime.now(timezone.utc)

    def rollup_history(self, keep_last: int = 8):
        """Summarize older turns to keep history compact."""
        if len(self.history) <= keep_last:
            return
        older = self.history[:-keep_last]
        snippet_parts = []
        for msg in older:
            content = msg.get("content") or ""
            snippet_parts.append(f"{msg.get('role')}: {content[:120]}")
        snippet = " | ".join(snippet_parts)
        if snippet:
            if self.summary:
                self.summary = f"{self.summary} | {snippet}"
            else:
                self.summary = snippet
            if len(self.summary) > 2000:
                self.summary = self.summary[-2000:]
        self.history = self.history[-keep_last:]

    def update_slot(self, key: str, value: Any):
        if value:
            self.slots[key] = value

    def slot_snapshot(self) -> str:
        if not self.slots:
            return ""
        parts = [f"{k}={v}" for k, v in self.slots.items()]
        return "; ".join(parts)
