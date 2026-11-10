# Financial Bot

PT-BR expense tracking agent built with **LangChain** (`create_agent` + tools + middleware) and OpenAI.

- Text: "Gastei 48,90 no Ifood", "100 de gasolina", "700 de compra do mes mercado"
- Audio: record in the UI (or upload webm/ogg/mp3/m4a/wav). It is transcribed with `gpt-4o-mini-transcribe`
- Receipt photo (cupom fiscal): the model reads the TOTAL, store and date
- Queries: "quanto gastei esse mês?", "gastos com mercado", "apaga a última"

## Setup

```bash
cp .env.example .env          # set OPENAI_API_KEY
uv sync                       # creates .venv and installs everything
```

> If you see `VIRTUAL_ENV=... does not match the project environment`, another venv is active in your shell. Run `deactivate` (uv uses `./.venv` anyway).

## Run

```bash
# 1. Agent server + LangGraph Studio (http://127.0.0.1:2024)
uv run langgraph dev
#    Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

# 2. Agent Chat UI (http://localhost:3000)
cd ui
cp .env.example .env          # defaults already point to localhost:2024 / "agent"
pnpm install
pnpm dev
```

Expenses are saved to `data/expenses.db` (SQLite):

```bash
sqlite3 data/expenses.db "select * from expenses order by id desc limit 10"
```

## Checks

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd ui && pnpm lint && pnpm build
```

Tests use an in-memory database and a fake transcriber, so they need no network or API key.

## How it works

```mermaid
flowchart TD
    Client["Agent Chat UI (Next.js)<br/>or LangGraph Studio"]

    subgraph Server["langgraph dev - financial_bot.agent:agent"]
        MW["MultimodalInputMiddleware<br/>audio to text, image normalization"]
        Prompt["today_prompt<br/>PT-BR system prompt + today's date"]
        Model["gpt-5-mini (vision)"]
        Tools["Tools<br/>add / list / summarize / delete expense"]
        Repo["repository.py"]
        MW --> Prompt --> Model
        Model <-->|"tool calls / results"| Tools
        Tools --> Repo
    end

    STT["OpenAI transcription<br/>gpt-4o-mini-transcribe"]
    DB[("SQLite / Postgres")]

    Client -->|"text, image, audio"| MW
    MW <-->|"audio / transcript"| STT
    Repo -->|SQLAlchemy| DB
    Model -.->|"streamed reply"| Client
```

A typical voice message:

```mermaid
sequenceDiagram
    actor User
    participant UI as Agent Chat UI
    participant MW as MultimodalInputMiddleware
    participant STT as OpenAI transcription
    participant LLM as gpt-5-mini
    participant Tool as add_expense
    participant DB as Database

    User->>UI: records "100 de gasolina"
    UI->>MW: HumanMessage with audio block
    MW->>STT: audio bytes
    STT-->>MW: "100 de gasolina"
    MW->>LLM: same message id, audio replaced by text
    LLM->>Tool: add_expense(amount=100.00, category=transporte, source=audio)
    Tool->>DB: INSERT amount_cents=10000
    Tool-->>LLM: saved expense
    LLM-->>UI: confirmation in PT-BR
```

The rewritten message keeps its original id, so it replaces the audio message in the graph state and each audio is transcribed only once.

| File | What it does |
| --- | --- |
| `src/financial_bot/config.py` | Settings from env (`pydantic-settings`), timezone-aware `today()` |
| `src/financial_bot/db.py` | Engine, `session_scope()`, `Expense` table |
| `src/financial_bot/repository.py` | Data access + `R$` formatting (no LLM code) |
| `src/financial_bot/tools.py` | LangChain tools with Pydantic-validated input |
| `src/financial_bot/middleware.py` | Audio transcription, image normalization, dynamic prompt |
| `src/financial_bot/prompts.py` | PT-BR system prompt |
| `src/financial_bot/agent.py` | `create_agent(...)` - the graph `langgraph dev` serves |
| `ui/` | [Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) copy with audio upload, mic recording and audio preview |

Money is stored as integer cents (`amount_cents`) to avoid float rounding errors.

## Configuration

| Variable | Default |
| --- | --- |
| `OPENAI_API_KEY` | required |
| `DATABASE_URL` | `sqlite:///data/expenses.db` |
| `CHAT_MODEL` | `openai:gpt-5-mini` |
| `TRANSCRIBE_MODEL` | `gpt-4o-mini-transcribe` |
| `TIMEZONE` | `America/Sao_Paulo` |
| `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` | optional tracing |

## Production

- **Postgres**: `uv add "psycopg[binary]"` and set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`. No code change.
- **Docker image**: `uv run langgraph build -t financial-bot`, or deploy to LangSmith Deployment (`langgraph.json` is ready).
- **UI**: deploy `ui/` to Vercel. See [ui/README.md](ui/README.md#going-to-production) for the API proxy and auth.
- **Schema changes**: tables are created on startup (`create_all`). Add Alembic once the schema starts to change.
- **Not yet included**: multi-user support (all expenses belong to one user) and auth in front of the agent server.
