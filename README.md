# Voice Agent Studio

A self-hosted platform for voice agents: build an agent in a visual flow builder, give it
knowledge from uploaded documents, test it in the browser by chat or voice, then put it on a phone
number or call a list of contacts with it.

> Work in progress. Phase 0 (the runnable stack) is in place; agents, knowledge bases and the
> flow builder come next.

## Stack

| Part | Technology |
|---|---|
| Console (`console/`) | Next.js, TypeScript, Tailwind |
| Control plane API (`api/`) | FastAPI, SQLAlchemy, Postgres with pgvector |
| Agent runtime (`runtime/`) | LiveKit Agents (Python), LangChain |
| Local services | Docker Compose: Postgres, Redis, RustFS (S3-compatible storage) |

## Run it locally

```powershell
Copy-Item .env.example .env.local   # then fill in the LiveKit and OpenAI keys
docker compose up -d --build
```

- Console: http://localhost:3000 (the Services card shows every part's health)
- API health: http://localhost:8000/health

## Develop

Each Python app has its own virtual environment:

```powershell
cd api   # or runtime
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check . ; .\.venv\Scripts\ruff.exe format --check .
```

The console:

```powershell
cd console
npm install
npm run dev      # http://localhost:3000
npm run lint ; npm run format:check ; npm run build
```

## License

MIT
