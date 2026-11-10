# Financial Bot - Chat UI

Next.js chat interface for the Financial Bot agent. It is based on [Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) (MIT, see [LICENSE](LICENSE)) and extended for expense input by voice and receipt photo.

## Changes from upstream

- **Mic recording** (`src/components/thread/record-button.tsx`): records audio in the browser and attaches it to the message
- **Audio upload** (`src/hooks/use-file-upload.tsx`, `src/lib/multimodal-utils.ts`): accepts webm, ogg, mp3, m4a and wav files and sends them as audio content blocks
- **Audio preview** (`src/components/thread/MultimodalPreview.tsx`): plays attached audio before sending

Transcription happens on the agent side (`MultimodalInputMiddleware`), so the UI only sends the raw audio block.

## Run

```bash
cp .env.example .env    # defaults point to the local agent server
pnpm install
pnpm dev                # http://localhost:3000
```

Start the agent first with `uv run langgraph dev` from the repository root.

| Variable                   | Default                 | Notes                                                             |
| -------------------------- | ----------------------- | ----------------------------------------------------------------- |
| `NEXT_PUBLIC_API_URL`      | `http://localhost:2024` | LangGraph server, or `<site>/api` behind the proxy                |
| `NEXT_PUBLIC_ASSISTANT_ID` | `agent`                 | Graph id from `langgraph.json`                                    |
| `LANGGRAPH_API_URL`        | -                       | Production only, used by the API proxy                            |
| `LANGSMITH_API_KEY`        | -                       | Production only, server side. Never prefix it with `NEXT_PUBLIC_` |

## Checks

```bash
pnpm lint && pnpm format:check && pnpm build
```

## Going to production

By default the browser talks to the LangGraph server directly, which only works locally.

1. Set `LANGGRAPH_API_URL` to the deployed agent and `NEXT_PUBLIC_API_URL` to `<your-site>/api`. The route `src/app/api/[..._path]/route.ts` proxies requests and injects `LANGSMITH_API_KEY` on the server.
2. The proxy does **not** authenticate callers. Before exposing it, put auth in front of it, or set up [LangGraph custom auth](https://docs.langchain.com/langsmith/auth) on the deployment, delete the proxy route and pass the user token through `defaultHeaders` in `src/providers/Stream.tsx`.
