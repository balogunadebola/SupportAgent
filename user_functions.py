# SupportAgent/user_functions.py
import json
from pathlib import Path
from typing import Any, Callable, Set
from data.catalog_repository import CatalogRepository
from services.order_service import OrderService

# Init
catalog_repo   = CatalogRepository()
order_service  = OrderService(catalog_repo)

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
        return to_json({"error":"Category required.","user_reply":"Please specify a category."})
    laptops = catalog_repo.get_laptops_in_category(category)
    if not laptops:
        return to_json({"error":"No laptops here.","user_reply":f"No laptops in '{category}'."})
    lines = [f"{m}: ${d['price']:.2f} ({d['specs']})" for m,d in laptops.items()]
    return to_json({"laptops":laptops,"user_reply":"\n".join(lines)})

def get_laptop_details(model: str) -> str:
    if not model:
        return to_json({"error":"Model required.","user_reply":"Please specify a model."})
    details = catalog_repo.get_laptop_details(model)
    if not details:
        return to_json({"error":"Not found.","user_reply":f"Couldn't find '{model}'."})
    return to_json({
        "details": details,
        "user_reply": f"{model}: ${details['price']:.2f}, {details['specs']}"
    })

def process_sales_order(name: str, email_address: str, product: str, quantity: int) -> str:
    # call your JSON‐only service
    result = order_service.process_order(name, email_address, product, quantity)
    order_number = result["order_number"]

    # write a .txt summary next to the JSON
    txt_name = f"order-{order_number}.txt"
    txt_path = Path(__file__).parent / "data" / "orders" / txt_name

    # Ensure the 'orders' directory exists
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the order summary to a .txt file
    txt_path.write_text(
        f"Order Number: {order_number}\n"
        f"Customer: {name} <{email_address}>\n"
        f"Product: {product} (x{quantity})\n"
        f"Total: ${result['total_price']:.2f}\n",
        encoding="utf-8"
    )

    # craft your user_reply
    return json.dumps({
        "user_reply": (
            f"Your order {order_number} has been placed! "
            f"I've saved your summary as {txt_name}."
        ),
        **{k: result[k] for k in ("order_number", "total_price")}
    })

def submit_support_ticket(email_address: str, order_number: str, description: str) -> str:
    if not all([email_address,order_number,description]):
        return to_json({
            "error":"All fields required.",
            "user_reply":"Email, order number, and description please."
        })
    ticket_id = f"TICKET-{order_number}"

    # Ensure the 'tickets' directory exists
    ticket_path = Path(__file__).parent / "data" / "tickets" / f"{ticket_id}.txt"
    ticket_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the support ticket details to a .txt file
    ticket_path.write_text(
        f"Ticket ID: {ticket_id}\n"
        f"Email: {email_address}\n"
        f"Order Number: {order_number}\n"
        f"Description: {description}\n",
        encoding="utf-8"
    )

    return to_json({
        "ticket_id": ticket_id,
        "user_reply": f"Support ticket {ticket_id} created. We'll provide you with an update on that email address."
    })

# export for main.py
user_functions: Set[Callable[...,Any]] = {
    route_to_agent,
    get_laptop_categories,
    get_laptops_in_category,
    get_laptop_details,
    process_sales_order,
    submit_support_ticket
}
