# 周末搭子 Backend

FastAPI backend for the 周末搭子 WeChat mini-program.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run
uvicorn app.main:app --reload

# Test
pytest tests/
```

## API Endpoints

- `GET /health` — Health check
- `POST /api/v1/chat/message` — Send message (SSE streaming)
- `GET /api/v1/chat/history/{sid}` — Chat history
- `POST /api/v1/plan/select` — Select a plan
- `POST /api/v1/plan/reject` — Reject plans
- `GET /api/v1/plan/detail/{pid}` — Plan detail
- `POST /api/v1/auth/wx-login` — WeChat login (stub)

## W1 Status

All external services (LLM, weather, map, Redis, DB) are **mocked**. Services have clear interfaces for W2 swap.
