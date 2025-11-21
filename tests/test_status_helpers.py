import json
from pathlib import Path

import pytest

import user_functions
from user_functions import get_order_status, get_ticket_status


@pytest.fixture
def temp_data_dirs(tmp_path, monkeypatch):
    orders_dir = tmp_path / "orders"
    tickets_dir = tmp_path / "tickets"
    orders_dir.mkdir()
    tickets_dir.mkdir()
    monkeypatch.setattr(user_functions, "ORDERS_DIR", orders_dir)
    monkeypatch.setattr(user_functions, "TICKETS_DIR", tickets_dir)
    return orders_dir, tickets_dir


def test_get_order_status_success(temp_data_dirs):
    orders_dir, _ = temp_data_dirs
    sample = orders_dir / "ORDER-TEST.txt"
    sample.write_text(
        "Order ID: ORDER-TEST\nStatus: Shipped\nSummary: Demo order\n\nDetails here",
        encoding="utf-8",
    )
    resp = json.loads(get_order_status("ORDER-TEST"))
    assert resp["status"] == "Shipped"
    assert "Demo order" in resp["user_reply"]


def test_get_order_status_not_found(temp_data_dirs):
    resp = json.loads(get_order_status("ORDER-NOPE"))
    assert resp["error"] == "Order not found"


def test_get_ticket_status_success(temp_data_dirs):
    _, tickets_dir = temp_data_dirs
    sample = tickets_dir / "TICKET-1234.txt"
    sample.write_text(
        "Ticket ID: TICKET-1234\nStatus: Open\nSummary: Screen issue\n\nDetails",
        encoding="utf-8",
    )
    resp = json.loads(get_ticket_status("TICKET-1234"))
    assert resp["status"] == "Open"
    assert "Screen issue" in resp["user_reply"]
