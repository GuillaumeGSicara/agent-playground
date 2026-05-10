# Agent Playground

## Goal

Build a Python agent that is fully compatible with the **Agent2Agent (A2A) protocol** — an open standard for communication and interoperability between AI agent systems.

The agent must expose an A2A-compliant server that any A2A client can discover and interact with, regardless of the underlying framework or vendor.

Full A2A specification: [`docs/a2a-specification.md`](docs/a2a-specification.md)

---

## What the agent must implement

### 1. AgentCard endpoint

Publish a JSON `AgentCard` at a well-known URL (e.g. `GET /.well-known/agent.json`) declaring:
- Agent identity (name, description, URL)
- Supported capabilities (`streaming`, `pushNotifications`, `extendedAgentCard`)
- Skills (what the agent can do)
- Security scheme

### 2. Core message operations

| JSON-RPC method | Description |
|---|---|
| `a2a_sendMessage` | Accept a user message, return a Task or direct Message |
| `a2a_sendStreamingMessage` | Stream real-time updates (SSE or WebSocket) until task completion |

### 3. Task management

| JSON-RPC method | Description |
|---|---|
| `a2a_getTask` | Return current task state + optional message history |
| `a2a_cancelTask` | Cancel a running task (idempotent) |

### 4. Task lifecycle

Tasks must transition through A2A states:

```
SUBMITTED → WORKING → COMPLETED
                    → INPUT_REQUIRED  (mid-task clarification)
                    → FAILED
                    → CANCELED
```

---

## Architecture

```
agent-playground/
├── src/
│   └── agent_playground/
│       ├── agent.py          # Core agent logic
│       ├── a2a_server.py     # A2A-compliant HTTP/JSON-RPC server
│       ├── agent_card.py     # AgentCard definition
│       ├── task_store.py     # In-memory task state management
│       └── settings.py       # pydantic-settings configuration
├── tests/
├── docs/
│   └── a2a-specification.md  # Full A2A spec (reference)
└── pyproject.toml
```

---

## Conventions

- **Language**: Python 3.11+, managed with `uv`
- **Settings**: All config via `pydantic-settings` and `.env` — never `os.getenv` directly
- **Types**: Full type annotations on every function, variable, and return value
- **Models**: Use `pydantic.BaseModel` for all structured data (Tasks, Messages, Parts, AgentCard)
- **Quality**: `ruff` for formatting/linting, `mypy` for type checking, `pytest` for tests
- **Pre-commit**: All checks run via `uv run pre-commit run --all-files`

See [`docs/a2a-specification.md`](docs/a2a-specification.md) for the full protocol reference.
