# SupportAgent

SupportAgent is a laptop sales/support assistant with three entry points:
- `api.py`: FastAPI backend exposing `/chat`, `/tickets`, `/orders`.
- `web_app.py`: Streamlit client for chat + ticket/order views.
- `main.py`: CLI chat mode.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate  # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create `.env` with your Azure OpenAI settings:
```
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-model-name
```

### Backend
```bash
uvicorn api:app --reload --port 8000
```

### Frontend
```bash
streamlit run web_app.py
```
If the API isn’t running on `http://localhost:8000`, set `support_api_url` in `.streamlit/secrets.toml`.

### CLI
```bash
python main.py
```

## Data layout
- Orders: `data/orders/ORDER-xxxx.(txt|json)`
- Tickets: `data/tickets/TICKET-xxxx.txt`

Files follow this shape:
```
Order ID: ORDER-123
Status: Pending
Created At: 2025-11-20T11:05:00Z
Summary: Laptop X with 16GB RAM and 512GB SSD

<full order details>
```

Legacy files lacking `Status` or `Created At` default to `Status: Open/Pending` and infer timestamps from file metadata.
