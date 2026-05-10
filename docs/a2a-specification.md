# Agent2Agent (A2A) Protocol Specification

> Source: https://a2a-protocol.org/latest/specification/
> Fetched: 2026-05-10

## Overview

The Agent2Agent (A2A) Protocol is an open standard designed to facilitate communication and interoperability between independent, potentially opaque AI agent systems. It enables agents built on different frameworks to discover capabilities, negotiate interaction modes, and manage collaborative tasks without exposing internal state.

Originally developed by Google and donated to the Linux Foundation.

- Official docs: https://a2a-protocol.org/latest/
- GitHub: https://github.com/a2aproject/A2A

---

## Core Architecture

A2A uses a **three-layer specification model**:

1. **Data Model Layer** — Protocol Buffer definitions of core structures (Task, Message, AgentCard, Part, Artifact)
2. **Abstract Operations Layer** — Binding-independent capabilities (Send Message, Stream, Get Task, etc.)
3. **Protocol Bindings Layer** — Concrete mappings to JSON-RPC, gRPC, and HTTP/REST

The normative source is `spec/a2a.proto`; all implementations must be generated from this Protocol Buffer definition.

---

## Key Concepts

### AgentCard

JSON metadata published by agents at a well-known URL describing:
- Identity (name, description, URL)
- Capabilities (streaming, push notifications, extended cards)
- Skills (what the agent can do)
- Endpoints
- Security schemes

Clients use the AgentCard to discover what an agent supports before interacting with it.

### Task

The fundamental unit of work, identified by a unique server-generated ID.

Lifecycle states:
- `SUBMITTED` → `WORKING` → `COMPLETED`
- Interrupted states: `INPUT_REQUIRED`, `AUTH_REQUIRED`
- Terminal failure states: `FAILED`, `CANCELED`, `REJECTED`

### Message

A communication unit with a `role` (user/agent), containing one or more `Part` objects. Messages can reference tasks and contexts for multi-turn interactions.

### Part

The smallest content unit within messages/artifacts. Each Part contains exactly one of:
- `text` (string)
- `raw` (bytes)
- `url` (reference)
- `data` (structured JSON)

All parts support an optional `mediaType` (MIME type).

### Artifact

Task output composed of multiple Parts. Each artifact has a unique ID, optional name/description, and metadata. Streaming supports incremental artifact delivery via `append` and `lastChunk` flags.

---

## Core Operations

### Message Operations

| Operation | Description |
|---|---|
| `a2a_sendMessage` | Client sends message, receives Task or direct Message response |
| `a2a_sendStreamingMessage` | Real-time updates via stream until task completion |

Both support a `returnImmediately` flag; default blocks until terminal/interrupted state.

### Task Management

| Operation | Description |
|---|---|
| `a2a_getTask` | Retrieve task state with optional message history via `historyLength` |
| `a2a_listTasks` | Paginate tasks with context/status filtering, cursor-based pagination |
| `a2a_cancelTask` | Request task cancellation (idempotent) |
| `a2a_subscribeToTask` | Stream updates for an existing task |

### Push Notification Operations

| Operation | Description |
|---|---|
| `a2a_createPushNotificationConfig` | Register webhook with a task |
| `a2a_getPushNotificationConfig` | Retrieve configuration details |
| `a2a_listPushNotificationConfigs` | Enumerate all webhooks for a task |
| `a2a_deletePushNotificationConfig` | Remove configuration (idempotent) |

### Agent Discovery

| Operation | Description |
|---|---|
| `a2a_getExtendedAgentCard` | Retrieve authenticated extended card (if `capabilities.extendedAgentCard = true`) |

---

## Update Delivery Mechanisms

Three complementary patterns:

1. **Polling** (`getTask`) — Simple, higher latency
2. **Streaming** (`sendStreamingMessage`, `subscribeToTask`) — Real-time, requires persistent connection
3. **Push Notifications** (webhook) — HTTP POST to client endpoint, asynchronous; preferred for long-running tasks

---

## Multi-Turn Interactions

- **Context ID**: Logically groups related tasks/messages. Server-generated or client-provided. Enables conversation continuity.
- **Task ID**: Always server-generated for new tasks.

Patterns:
| Request contains | Behavior |
|---|---|
| Same `contextId`, no `taskId` | Start new task in conversation |
| Same `taskId` and `contextId` | Continue existing task |
| `taskId` alone | Server infers `contextId` |
| Mismatched IDs | Server rejects request |

---

## Streaming Events

### TaskStatusUpdateEvent
Fields: `taskId`, `contextId`, `status` (TaskStatus object), optional metadata.

### TaskArtifactUpdateEvent
Fields: `taskId`, `contextId`, `artifact`, optional `append` (concatenate to previous) and `lastChunk` flags.

### StreamResponse
One-of container carrying: Task, Message, TaskStatusUpdateEvent, or TaskArtifactUpdateEvent.

---

## Protocol Bindings

### JSON-RPC 2.0 (primary)
Method names: `a2a_sendMessage`, `a2a_sendStreamingMessage`, `a2a_getTask`, `a2a_listTasks`, `a2a_cancelTask`, `a2a_subscribeToTask`, etc.

### gRPC
Unary and server-streaming RPC methods. gRPC metadata carries service parameters.

### HTTP/REST

| Method | Endpoint | Operation |
|---|---|---|
| POST | `/messages` | SendMessage |
| POST | `/messages:stream` | SendStreamingMessage |
| GET | `/tasks/{id}` | GetTask |
| GET | `/tasks` | ListTasks |

---

## Authentication & Authorization

Agents declare security schemes in AgentCard:
- API Key
- HTTP Basic / Bearer
- OAuth2
- OpenID Connect
- Mutual TLS

**Client responsibilities**: Send `A2A-Version` header (defaults to `0.3` if empty); authenticate per declared scheme.

**Server responsibilities**: Validate credentials, enforce authorization scoping, return appropriate errors.

---

## Versioning

Protocol identified by `Major.Minor` (e.g., `1.0`). Clients must send the `A2A-Version` service parameter; servers process using requested version semantics or return `VersionNotSupportedError`.

---

## Error Handling

All errors must convey:
- Machine-readable code
- Human-readable message
- Optional structured details (using `google.rpc` types)

A2A-specific errors:
- `TaskNotFoundError`
- `PushNotificationNotSupportedError`
- `VersionNotSupportedError`
- `ContentTypeNotSupportedError`

---

## Implementation Notes

- **Idempotency**: Get operations are naturally idempotent; Send may detect duplicates via `messageId`; Cancel is idempotent.
- **Event Ordering**: Streaming must preserve event order; multiple concurrent streams are allowed per task.
- **History Semantics**: `historyLength=0` omits messages; unset means default limit; `>0` returns at most N recent messages.
- **Capability Validation**: When clients use operations not declared as supported, the agent must return an appropriate error.
