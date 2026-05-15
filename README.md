# agent-playground

![agent-to-agent](./public/agent-to-agent-badge.svg) ![ag-ui](./public/ag-ui-badge.svg)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)  ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Next JS](https://img.shields.io/badge/Next-black.svg?style=for-the-badge&logo=next.js&logoColor=white)

A Python agent that speaks both the [A2A protocol](docs/a2a-specification.md) (agent-to-agent) and the [AG-UI protocol](https://docs.ag-ui.com) (agent-to-UI), with Tavily web search, [data.gouv.fr](https://data.gouv.fr) open-data access via MCP, and an OpenAI-compatible inference backend.

## Boot

```bash
# 1. Install dependencies
uv sync

# 2. Configure
cp .env.template .env
# Edit .env — set OPENAI_API_BASE_URL, OPENAI_API_KEY, MODEL_NAME, TAVILY_API_KEY

# 3. Run the agent server
task run          # or: uv run python -m agent_playground

# 4. (Optional) Run the chat UI
task ui:install   # first time only
task ui           # starts Next.js on http://localhost:3000
```

The agent server starts on `http://0.0.0.0:8000` by default (`AGENT_HOST` / `AGENT_PORT` in `.env`).

### Endpoints

| Method | Path | Protocol |
|--------|------|----------|
| `GET` | `/.well-known/agent-card.json` | A2A — agent discovery |
| `POST` | `/` | A2A — JSON-RPC (sendMessage, getTask, …) |
| `POST` | `/invocations` | AG-UI — SSE event stream |
| `GET` | `/ping` | Health check |

### Taskfile shortcuts

| Task | Description |
|------|-------------|
| `task run` | Start the agent server |
| `task ui` | Start the Next.js chat UI dev server |
| `task ask` | Send a question via AG-UI (curl) |
| `task ask:pretty` | Same, pretty-printed SSE events |
| `task ask:search` | Force a web-search tool call |
| `task check:events` | Show only the event-type sequence |
| `task card` | Fetch the A2A agent card |
| `task ping` | Health check |

## Architecture

Three tiers, each in its own package:

```
src/agent_playground/
│
├── server/          # Tier 1 — Protocol / Transport
│   ├── app.py         Starlette app; wires A2A routes and AG-UI endpoints
│   └── card.py        Builds the A2A AgentCard
│
├── services/        # Tier 2 — Orchestration
│   ├── agent.py       ReAct loop — async-generates AgentEvents (text chunks, tool calls)
│   ├── executor.py    A2A adapter  — translates AgentEvents → TaskArtifactUpdateEvent
│   └── agui.py        AG-UI adapter — translates AgentEvents → SSE TEXT_MESSAGE / TOOL_CALL events
│
├── infrastructure/  # Tier 3 — External services
│   ├── llm.py         AsyncOpenAI client (configurable base_url for any OpenAI-compatible API)
│   ├── search.py      WebSearchTool — Tavily async client
│   └── datagouv_mcp.py  DatagouvMCPClient — fetches & dispatches tools from data.gouv.fr MCP
│
├── models/          # Cross-tier Pydantic models
│   ├── messages.py    LLM message types (SystemMessage, UserMessage, AssistantMessage, …)
│   ├── tools.py       Tool definition schema (ToolDefinition, ToolFunction, …)
│   └── events.py      Agent event types (TextChunkEvent, ToolCallStartEvent, …)
│
├── prompts/         # Markdown prompt files
│   └── system_prompt.md
│
├── constants.py     StrEnums + module-level constants (AgentMeta, ToolName, PROJECT_ROOT, …)
├── settings.py      AgentSettings — pydantic-settings, reads from .env
└── configuration.py Dependency wiring (LLMClient, tool providers, agent, handlers)
```

Both `executor.py` and `agui.py` consume the same `Agent.run()` async generator — protocol translation is the only difference between them.

The `Agent` accepts a list of `ToolProvider` objects (anything implementing `list_definitions` / `handle_call`). `WebSearchTool` and `DatagouvMCPClient` both satisfy this interface and are composed at startup.
