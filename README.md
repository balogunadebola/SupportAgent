# SupportAgent

SupportAgent is an AI assistant that routes between sales and support. It now exposes:
- A FastAPI backend (`api.py`) with chat, tickets, and orders endpoints.
- A Streamlit frontend (`web_app.py`) that calls the API.
- A CLI entry point (`main.py`) from the original version.

### Running the backend
```bash
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Place your Azure OpenAI credentials in `.env` using the same keys as the CLI (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT_NAME`).

### Running the frontend
```bash
streamlit run web_app.py
```
If the API is not on `http://localhost:8000`, set `support_api_url` in `.streamlit/secrets.toml`.

### Data locations and format
- Orders are stored under `data/orders/`
- Tickets are stored under `data/tickets/`

Ticket files include:
```
Ticket ID: TICKET-123
Status: Open
Created At: 2025-11-20T10:23:00Z
Summary: Short issue summary

<free-form content>
```

Order files include:
```
Order ID: ORDER-123
Status: Pending
Created At: 2025-11-20T11:05:00Z
Summary: Laptop X with 16GB RAM and 512GB SSD

<full order details>
```
Legacy files without `Status` or `Created At` default to `Status: Open/Pending` and the timestamp inferred from file metadata.
