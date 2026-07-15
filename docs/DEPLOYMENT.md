# Deployment Guide

The Voice Agent can run three ways: as a **desktop GUI**, a **headless CLI**, or a
**FastAPI backend**. This guide covers packaging and server deployment.

## 1. Desktop distribution (PyInstaller)

Bundle the GUI into a single executable:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name VoiceAgent \
  --add-data "database/schema.sql:database" \
  main.py
```

The build appears under `dist/VoiceAgent/`. Ship `.env.example` alongside and instruct
users to create their own `.env`. On Windows drop the `--windowed` flag if you want a
console for logs.

## 2. Headless / server (FastAPI)

Run the decoupled API for remote frontends or integrations:

```bash
python main.py --server
# or directly with uvicorn / gunicorn workers:
uvicorn server:create_app --factory --host 0.0.0.0 --port 8765
```

Endpoints:

| Method | Path      | Purpose                                  |
|--------|-----------|------------------------------------------|
| GET    | `/health` | Status, online flag, platform, tool count|
| GET    | `/tools`  | List all registered tools                |
| POST   | `/chat`   | `{"message": "..."}` → `{"reply": "..."}`|
| WS     | `/ws`     | Stream agent events + final reply        |

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV VA_API_HOST=0.0.0.0
EXPOSE 8765
CMD ["python", "main.py", "--server"]
```

```bash
docker build -t voice-agent .
docker run -p 8765:8765 --env-file .env voice-agent
```

> The GUI is **not** intended for containers (no display). Desktop-automation tools
> (mouse/keyboard/apps) only make sense on a machine with a real desktop session; in a
> server deployment they will report that no display is available.

## 3. Production notes

- **Secrets**: never bake `VA_OPENAI_API_KEY` into an image; pass it via `--env-file`
  or a secrets manager.
- **Logs**: structured JSONL is written to `VA_LOG_DIR`. Ship these to your log stack;
  `latency.jsonl` is convenient for latency dashboards.
- **Database**: `VA_DB_PATH` should point at a persistent volume so memory survives
  restarts.
- **Reverse proxy**: front the FastAPI server with nginx/Caddy for TLS.
- **Scaling**: the agent is stateful per process (SQLite + in-memory sessions); run one
  worker per user/session or externalise state before scaling horizontally.
