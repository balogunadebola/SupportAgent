"""
Streamlit frontend that talks to the FastAPI backend.
"""

import os
import uuid
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# Default to local backend; you can override with SUPPORT_API_URL env var if needed.
API_URL = os.getenv("SUPPORT_API_URL", "http://localhost:8000")


def _call_api(method: str, path: str, **kwargs) -> Optional[requests.Response]:
    url = f"{API_URL}{path}"
    try:
        return requests.request(method, url, timeout=10, **kwargs)
    except requests.RequestException as exc:
        st.error(f"Could not reach backend: {exc}")
        return None


def _ensure_session():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "history" not in st.session_state:
        st.session_state.history = []


def render_chat():
    st.header("Chat with SupportAgent")
    if not st.session_state.history:
        with st.chat_message("assistant"):
            st.markdown("Hi! I can help with laptop purchases or support. What do you need?")
    history: List[Dict[str, str]] = st.session_state.history
    display_history = [m for m in history if m.get("role") in {"user", "assistant"}]
    for msg in display_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about products or support..."):
        # Show the user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        payload = {
            "session_id": st.session_state.session_id,
            "message": prompt,
            "history": history,
        }
        resp = _call_api("post", "/chat", json=payload)
        if not resp:
            return
        if resp.status_code == 429:
            st.warning(resp.json().get("detail", "Rate limit exceeded"))
            return
        if resp.status_code != 200:
            st.error(f"Backend error: {resp.text}")
            return
        data = resp.json()
        reply = data.get("reply", "")
        updated_history = data.get("updated_history", history)
        st.session_state.history = updated_history
        with st.chat_message("assistant"):
            st.markdown(reply)


def render_tickets():
    st.header("Tickets")
    resp = _call_api("get", "/tickets")
    if not resp:
        return
    if resp.status_code != 200:
        st.error(f"Could not load tickets: {resp.text}")
        return
    tickets: List[Dict[str, Any]] = resp.json().get("tickets", [])
    if not tickets:
        st.info("No tickets yet.")
        return
    ticket_ids = [t["ticket_id"] for t in tickets]
    st.dataframe(tickets, use_container_width=True)
    selected = st.selectbox("Pick a ticket", ticket_ids)
    if selected:
        detail_resp = _call_api("get", f"/tickets/{selected}")
        if detail_resp and detail_resp.status_code == 200:
            ticket = detail_resp.json().get("ticket", {})
            st.subheader(f"{ticket.get('ticket_id')}")
            st.write(f"Status: **{ticket.get('status')}**")
            st.write(f"Created: {ticket.get('created_at')}")
            st.write(f"Summary: {ticket.get('summary')}")
            st.text_area("Content", ticket.get("content", ""), height=200, disabled=True)

            new_status = st.selectbox("Update status", ["Open", "In Progress", "Resolved"], index=0)
            if st.button("Apply status"):
                upd = _call_api("put", f"/tickets/{selected}/status", json={"status": new_status})
                if upd and upd.status_code == 200:
                    st.success("Ticket status updated")
                else:
                    st.error(f"Could not update ticket: {upd.text if upd else 'no response'}")


def render_orders():
    st.header("Orders")
    resp = _call_api("get", "/orders")
    if not resp:
        return
    if resp.status_code != 200:
        st.error(f"Could not load orders: {resp.text}")
        return
    orders: List[Dict[str, Any]] = resp.json().get("orders", [])
    if not orders:
        st.info("No orders yet.")
        return
    order_ids = [o["order_id"] for o in orders]
    st.dataframe(orders, use_container_width=True)
    selected = st.selectbox("Pick an order", order_ids)
    if selected:
        detail_resp = _call_api("get", f"/orders/{selected}")
        if detail_resp and detail_resp.status_code == 200:
            order = detail_resp.json().get("order", {})
            st.subheader(f"{order.get('order_id')}")
            st.write(f"Status: **{order.get('status')}**")
            st.write(f"Created: {order.get('created_at')}")
            st.write(f"Summary: {order.get('summary')}")
            st.text_area("Content", order.get("content", ""), height=200, disabled=True)

            new_status = st.selectbox("Update order status", ["Pending", "Processing", "Completed", "Cancelled"], index=0)
            if st.button("Apply order status"):
                upd = _call_api("put", f"/orders/{selected}/status", json={"status": new_status})
                if upd and upd.status_code == 200:
                    st.success("Order status updated")
                else:
                    st.error(f"Could not update order: {upd.text if upd else 'no response'}")


def main():
    st.set_page_config(page_title="SupportAgent", page_icon="SA", layout="wide")
    _ensure_session()
    st.sidebar.title("SupportAgent")
    view = st.sidebar.radio(
        "Navigate",
        ["Chat", "Tickets", "Orders"],
        format_func=lambda x: {"Chat": "Chat", "Tickets": "Tickets", "Orders": "Orders"}[x],
    )

    if view == "Chat":
        render_chat()
    elif view == "Tickets":
        render_tickets()
    else:
        render_orders()


if __name__ == "__main__":
    main()
