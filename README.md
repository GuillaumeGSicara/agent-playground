# agent-playground

A Python agent that speaks both the [A2A protocol](docs/a2a-specification.md) (agent-to-agent) and the [AG-UI protocol](https://docs.ag-ui.com) (agent-to-UI), with a web-search tool and an OpenAI-compatible inference backend.

## Boot

```bash
# 1. Install dependencies
uv sync

# 2. Configure
cp .env.template .env
# Edit .env — set OPENAI_API_BASE_URL, OPENAI_API_KEY, MODEL_NAME

# 3. Run
uv run python -m agent_playground
```

The server starts on `http://0.0.0.0:8000` by default (`AGENT_HOST` / `AGENT_PORT` in `.env`).

### Endpoints

| Method | Path | Protocol |
|--------|------|----------|
| `GET` | `/.well-known/agent-card.json` | A2A — agent discovery |
| `POST` | `/` | A2A — JSON-RPC (sendMessage, getTask, …) |
| `POST` | `/invocations` | AG-UI — SSE event stream |
| `GET` | `/ping` | Health check |

## Architecture

Three tiers, each in its own package:

```
src/agent_playground/
│
├── server/          # Tier 1 — Protocol / Transport
│   └── app.py         Starlette app; wires A2A routes and AG-UI endpoints
│
├── execution/       # Tier 2 — Orchestration
│   ├── agent.py       ReAct loop — async-generates AgentEvents (text chunks, tool calls)
│   ├── executor.py    A2A adapter  — translates AgentEvents → TaskArtifactUpdateEvent
│   └── agui.py        AG-UI adapter — translates AgentEvents → SSE TEXT_MESSAGE / TOOL_CALL events
│
├── infrastructure/  # Tier 3 — External services
│   ├── llm.py         AsyncOpenAI client (configurable base_url for any OpenAI-compatible API)
│   └── search.py      WebSearchTool (mock — Tavily integration deferred, see TODO_validators.md)
│
├── models/          # Cross-tier Pydantic models
│   ├── messages.py    LLM message types (SystemMessage, UserMessage, AssistantMessage, …)
│   ├── tools.py       Tool definition schema (ToolDefinition, ToolFunction, …)
│   └── events.py      Agent event types (TextChunkEvent, ToolCallStartEvent, …)
│
├── constants.py     StrEnums + module-level constants (SYSTEM_PROMPT, PROJECT_ROOT, …)
├── settings.py      AgentSettings — pydantic-settings, reads from .env
└── card.py          Builds the A2A AgentCard (protobuf)
```

Both `executor.py` and `agui.py` consume the same `Agent.run()` async generator — protocol translation is the only difference between them.
