import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app_core import SupportAssistantCore
from config import settings
from models import (
    ChatRequest,
    ChatResponse,
    OrderDetailsModel,
    OrderDetailsResponse,
    OrderMetaModel,
    OrderStatusUpdateRequest,
    OrderStatusUpdateResponse,
    OrdersListResponse,
    TicketDetailsModel,
    TicketDetailsResponse,
    TicketMetaModel,
    TicketStatusUpdateRequest,
    TicketStatusUpdateResponse,
    TicketsListResponse,
)
from user_functions import (
    OrderDetails,
    OrderMeta,
    TicketDetails,
    TicketMeta,
    get_order,
    get_ticket,
    list_orders,
    list_tickets,
    update_order_status,
    update_ticket_status,
)
from utils.session_manager import session_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("support_api")

app = FastAPI(title="SupportAgent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

core = SupportAssistantCore({})


class RateLimiter:
    """
    Simple sliding-window rate limiter keyed by session_id.
    """

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.perf_counter()
        async with self.lock:
            window = self.calls[key]
            while window and now - window[0] > self.window:
                window.popleft()
            if len(window) >= self.max_calls:
                return False
            window.append(now)
            return True


rate_limiter = RateLimiter(
    max_calls=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


@app.middleware("http")
async def log_and_time_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error for %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request completed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": getattr(response, "status_code", None),
            "latency_ms": round(duration_ms, 2),
        },
    )
    return response


async def enforce_rate_limit(session_id: str = ""):
    allowed = await rate_limiter.allow(session_id or "anonymous")
    if not allowed:
        logger.warning("rate limit exceeded", extra={"session_id": session_id})
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a moment and try again.",
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    await enforce_rate_limit(payload.session_id)
    logger.info("chat request", extra={"session_id": payload.session_id})
    try:
        result = await core.handle_user_message(
            session_id=payload.session_id,
            user_message=payload.message,
            conversation_history=payload.history,
        )
    except Exception:
        logger.exception("chat endpoint failed")
        # Provide a controlled fallback
        result = {
            "reply": "I ran into a problem handling that message. Please try again shortly.",
            "updated_history": payload.history,
            "used_agent": "fallback",
            "tool_calls": [],
            "latency_ms": 0.0,
            "fallback_used": True,
        }
    return result


@app.get("/tickets", response_model=TicketsListResponse)
async def list_tickets_endpoint():
    tickets = list_tickets()
    return {"tickets": [TicketMetaModel(**asdict(t)) for t in tickets]}


@app.get("/tickets/{ticket_id}", response_model=TicketDetailsResponse)
async def ticket_details_endpoint(ticket_id: str):
    ticket: Optional[TicketDetails] = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket": TicketDetailsModel(**asdict(ticket))}


@app.put("/tickets/{ticket_id}/status", response_model=TicketStatusUpdateResponse)
async def ticket_status_update_endpoint(ticket_id: str, payload: TicketStatusUpdateRequest):
    updated = update_ticket_status(ticket_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    logger.info("ticket status updated", extra={"ticket_id": ticket_id, "status": payload.status})
    return {
        "success": True,
        "ticket_id": ticket_id,
        "new_status": payload.status,
        "message": "Ticket status updated.",
    }


@app.get("/orders", response_model=OrdersListResponse)
async def list_orders_endpoint():
    orders = list_orders()
    return {"orders": [OrderMetaModel(**asdict(o)) for o in orders]}


@app.get("/orders/{order_id}", response_model=OrderDetailsResponse)
async def order_details_endpoint(order_id: str):
    order: Optional[OrderDetails] = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": OrderDetailsModel(**asdict(order))}


@app.put("/orders/{order_id}/status", response_model=OrderStatusUpdateResponse)
async def order_status_update_endpoint(order_id: str, payload: OrderStatusUpdateRequest):
    updated = update_order_status(order_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")
    logger.info("order status updated", extra={"order_id": order_id, "status": payload.status})
    return {
        "success": True,
        "order_id": order_id,
        "new_status": payload.status,
        "message": "Order status updated.",
    }
