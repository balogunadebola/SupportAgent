"""
Functions used by the agents plus helpers for listing/updating ticket and order
files. The listing helpers are imported by the FastAPI layer.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional, Set

from data.catalog_repository import CatalogRepository
from services.order_service import OrderService

logger = logging.getLogger(__name__)

# Directories
BASE_DIR = Path(__file__).parent
TICKETS_DIR = BASE_DIR / "data" / "tickets"
ORDERS_DIR = BASE_DIR / "data" / "orders"

# Init
catalog_repo = CatalogRepository()
order_service = OrderService(catalog_repo)


@dataclass
class TicketMeta:
    ticket_id: str
    status: str
    created_at: Optional[str]
    summary: str


@dataclass
class TicketDetails:
    ticket_id: str
    status: str
    created_at: Optional[str]
    summary: str
    content: str


@dataclass
class OrderMeta:
    order_id: str
    status: str
    created_at: Optional[str]
    summary: str


@dataclass
class OrderDetails:
    order_id: str
    status: str
    created_at: Optional[str]
    summary: str
    content: str


def to_json(data: Any) -> str:
    return json.dumps(data)


def route_to_agent(target: str) -> str:
    valid = {"sales", "support"}
    if target not in valid:
        return to_json({"error": f"Invalid target '{target}'."})
    return to_json({"target": target})


def get_laptop_categories() -> str:
    cats = catalog_repo.get_categories()
    return to_json({
        "categories": cats,
        "user_reply": "Our categories are: " + ", ".join(cats)
    })


def get_laptops_in_category(category: str) -> str:
    if not category:
        return to_json({"error": "Category required.", "user_reply": "Please specify a category."})
    laptops = catalog_repo.get_laptops_in_category(category)
    if not laptops:
        return to_json({"error": "No laptops here.", "user_reply": f"No laptops in '{category}'."})
    lines = [f"{m}: ${d['price']:.2f} ({d['specs']})" for m, d in laptops.items()]
    return to_json({"laptops": laptops, "user_reply": "\n".join(lines)})


def get_laptop_details(model: str) -> str:
    if not model:
        return to_json({"error": "Model required.", "user_reply": "Please specify a model."})
    details = catalog_repo.get_laptop_details(model)
    if not details:
        return to_json({"error": "Not found.", "user_reply": f"Couldn't find '{model}'."})
    return to_json({
        "details": details,
        "user_reply": f"{model}: ${details['price']:.2f}, {details['specs']}"
    })


def process_sales_order(name: str, email_address: str, product: str, quantity: int) -> str:
    # call your JSON-only service
    result = order_service.process_order(name, email_address, product, quantity)
    order_number = result["order_number"]

    # write a .txt summary next to the JSON
    txt_name = f"order-{order_number}.txt"
    txt_path = ORDERS_DIR / txt_name

    # Ensure the 'orders' directory exists
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the order summary to a .txt file
    txt_path.write_text(
        f"Order ID: ORDER-{order_number}\n"
        f"Status: Pending\n"
        f"Created At: {datetime.utcnow().isoformat()}Z\n"
        f"Summary: {product} (x{quantity})\n\n"
        f"Order Number: {order_number}\n"
        f"Customer: {name} <{email_address}>\n"
        f"Product: {product} (x{quantity})\n"
        f"Total: ${result['total_price']:.2f}\n",
        encoding="utf-8"
    )

    # craft your user_reply
    return json.dumps({
        "user_reply": (
            f"Your order ORDER-{order_number} has been placed! "
            f"We'll email {email_address} with details and tracking next."
        ),
        **{k: result[k] for k in ("order_number", "total_price")}
    })


def submit_support_ticket(email_address: str, order_number: str, description: str) -> str:
    if not all([email_address, order_number, description]):
        return to_json({
            "error": "All fields required.",
            "user_reply": "Email, order number, and description please."
        })
    ticket_id = f"TICKET-{order_number}"

    # Ensure the 'tickets' directory exists
    ticket_path = TICKETS_DIR / f"{ticket_id}.txt"
    ticket_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the support ticket details to a .txt file
    ticket_path.write_text(
        f"Ticket ID: {ticket_id}\n"
        f"Status: Open\n"
        f"Created At: {datetime.utcnow().isoformat()}Z\n"
        f"Summary: Support request for order {order_number}\n\n"
        f"Email: {email_address}\n"
        f"Order Number: {order_number}\n"
        f"Description: {description}\n",
        encoding="utf-8"
    )

    return to_json({
        "ticket_id": ticket_id,
        "user_reply": (
            f"Support ticket {ticket_id} created. "
            f"We'll email updates to {email_address}. "
            f"If you have more details, reply with them and I'll add them to the ticket."
        )
    })


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("File not found while reading: %s", path)
        return ""
    except Exception:
        logger.exception("Failed to read file: %s", path)
        return ""


def _atomic_write(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
        return True
    except Exception:
        logger.exception("Failed atomic write for %s", path)
        return False


def _parse_created_at_from_mtime(path: Path) -> Optional[str]:
    try:
        ts = datetime.fromtimestamp(path.stat().st_mtime)
        return ts.isoformat() + "Z"
    except Exception:
        return None


def _canonical_order_id(path: Path) -> str:
    raw = path.stem
    if raw.upper().startswith("ORDER-"):
        return raw.upper()
    return f"ORDER-{raw.split('-')[-1]}".upper()


def _parse_ticket_file(path: Path) -> TicketDetails:
    text = _safe_read_text(path)
    lines = text.splitlines()
    meta = {
        "ticket_id": path.stem,
        "status": "Open",
        "created_at": None,
        "summary": ""
    }
    content_lines: List[str] = []

    for line in lines:
        if line.lower().startswith("ticket id:"):
            meta["ticket_id"] = line.split(":", 1)[1].strip() or meta["ticket_id"]
        elif line.lower().startswith("status:"):
            meta["status"] = line.split(":", 1)[1].strip() or meta["status"]
        elif line.lower().startswith("created at:"):
            meta["created_at"] = line.split(":", 1)[1].strip() or None
        elif line.lower().startswith("summary:"):
            meta["summary"] = line.split(":", 1)[1].strip()
        else:
            content_lines.append(line)

    if not meta["created_at"]:
        meta["created_at"] = _parse_created_at_from_mtime(path)
    if not meta["summary"]:
        meta["summary"] = (content_lines[0].strip() if content_lines else "") or "No summary available"
    content = "\n".join(content_lines).strip()
    return TicketDetails(
        ticket_id=meta["ticket_id"],
        status=meta["status"] or "Open",
        created_at=meta["created_at"],
        summary=meta["summary"],
        content=content or text,
    )


def list_tickets() -> List[TicketMeta]:
    tickets: List[TicketMeta] = []
    if not TICKETS_DIR.exists():
        return tickets
    for path in sorted(TICKETS_DIR.glob("*.txt")):
        details = _parse_ticket_file(path)
        tickets.append(TicketMeta(
            ticket_id=details.ticket_id,
            status=details.status,
            created_at=details.created_at,
            summary=details.summary
        ))
    return tickets


def get_ticket(ticket_id: str) -> Optional[TicketDetails]:
    path = TICKETS_DIR / f"{ticket_id}.txt"
    if not path.exists():
        return None
    return _parse_ticket_file(path)


def update_ticket_status(ticket_id: str, new_status: str) -> bool:
    path = TICKETS_DIR / f"{ticket_id}.txt"
    if not path.exists():
        logger.warning("Ticket not found: %s", ticket_id)
        return False
    details = _parse_ticket_file(path)
    updated_lines = [
        f"Ticket ID: {details.ticket_id}",
        f"Status: {new_status}",
        f"Created At: {details.created_at or ''}",
        f"Summary: {details.summary}",
        "",
        details.content or ""
    ]
    return _atomic_write(path, "\n".join(updated_lines).strip() + "\n")


def _parse_order_file(path: Path) -> OrderDetails:
    text = _safe_read_text(path)
    lines = text.splitlines()
    meta = {
        "order_id": _canonical_order_id(path),
        "status": "Pending",
        "created_at": None,
        "summary": ""
    }
    content_lines: List[str] = []

    for line in lines:
        if line.lower().startswith(("order id:", "order number:")):
            value = line.split(":", 1)[1].strip()
            meta["order_id"] = value.upper() if value else meta["order_id"]
        elif line.lower().startswith("status:"):
            meta["status"] = line.split(":", 1)[1].strip() or meta["status"]
        elif line.lower().startswith("created at:"):
            meta["created_at"] = line.split(":", 1)[1].strip() or None
        elif line.lower().startswith("summary:"):
            meta["summary"] = line.split(":", 1)[1].strip()
        else:
            content_lines.append(line)

    if not meta["created_at"]:
        meta["created_at"] = _parse_created_at_from_mtime(path)
    if not meta["summary"]:
        meta["summary"] = (content_lines[0].strip() if content_lines else "") or "No summary available"

    content = "\n".join(content_lines).strip()
    return OrderDetails(
        order_id=meta["order_id"],
        status=meta["status"] or "Pending",
        created_at=meta["created_at"],
        summary=meta["summary"],
        content=content or text,
    )


def list_orders() -> List[OrderMeta]:
    orders: List[OrderMeta] = []
    if not ORDERS_DIR.exists():
        return orders
    for path in sorted(ORDERS_DIR.glob("*.txt")):
        details = _parse_order_file(path)
        orders.append(OrderMeta(
            order_id=details.order_id,
            status=details.status,
            created_at=details.created_at,
            summary=details.summary
        ))
    return orders


def get_order(order_id: str) -> Optional[OrderDetails]:
    path = ORDERS_DIR / f"{order_id}.txt"
    if not path.exists():
        # Try lowercase variant for legacy naming
        alt = ORDERS_DIR / f"{order_id.lower()}.txt"
        path = alt if alt.exists() else path
    if not path.exists():
        return None
    return _parse_order_file(path)


def update_order_status(order_id: str, new_status: str) -> bool:
    path = ORDERS_DIR / f"{order_id}.txt"
    if not path.exists():
        alt = ORDERS_DIR / f"{order_id.lower()}.txt"
        path = alt if alt.exists() else path
    if not path.exists():
        logger.warning("Order not found: %s", order_id)
        return False
    details = _parse_order_file(path)
    updated_lines = [
        f"Order ID: {details.order_id}",
        f"Status: {new_status}",
        f"Created At: {details.created_at or ''}",
        f"Summary: {details.summary}",
        "",
        details.content or ""
    ]
    return _atomic_write(path, "\n".join(updated_lines).strip() + "\n")


def _status_payload(
    entity_id: str,
    status: str,
    summary: str,
    created_at: Optional[str],
    label: str,
) -> str:
    return to_json({
        f"{label}_id": entity_id,
        "status": status,
        "summary": summary,
        "created_at": created_at,
        "user_reply": f"{label.title()} {entity_id} is currently '{status}'. Summary: {summary}",
    })


def get_order_status(order_id: str) -> str:
    details = get_order(order_id)
    if not details:
        return to_json({
            "error": "Order not found",
            "user_reply": f"I couldn't find order {order_id}. Please double-check the ID.",
        })
    return _status_payload(details.order_id, details.status, details.summary, details.created_at, "order")


def get_ticket_status(ticket_id: str) -> str:
    details = get_ticket(ticket_id)
    if not details:
        return to_json({
            "error": "Ticket not found",
            "user_reply": f"I couldn't find ticket {ticket_id}. Please double-check the ID.",
        })
    return _status_payload(details.ticket_id, details.status, details.summary, details.created_at, "ticket")


# export for main.py
user_functions: Set[Callable[..., Any]] = {
    route_to_agent,
    get_laptop_categories,
    get_laptops_in_category,
    get_laptop_details,
    process_sales_order,
    submit_support_ticket,
    get_ticket_status,
    get_order_status,
}
# User-facing helpers for quick status checks
def get_order_status(order_id: str) -> str:
    details = get_order(order_id)
    if not details:
        return to_json({"error": "Order not found", "user_reply": f"I couldn't find order {order_id}. Please check the ID."})
    return to_json({
        "order_id": details.order_id,
        "status": details.status,
        "summary": details.summary,
        "created_at": details.created_at,
        "user_reply": f"Order {details.order_id} is currently '{details.status}'. Summary: {details.summary}"
    })


def get_ticket_status(ticket_id: str) -> str:
    details = get_ticket(ticket_id)
    if not details:
        return to_json({"error": "Ticket not found", "user_reply": f"I couldn't find ticket {ticket_id}. Please check the ID."})
    return to_json({
        "ticket_id": details.ticket_id,
        "status": details.status,
        "summary": details.summary,
        "created_at": details.created_at,
        "user_reply": f"Ticket {details.ticket_id} is currently '{details.status}'. Summary: {details.summary}"
    })
