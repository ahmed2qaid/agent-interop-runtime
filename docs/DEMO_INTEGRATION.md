# Demo Integration Contract

This repository remains the framework-neutral agent interoperability layer. The end-to-end demo uses it as the orchestration surface that can route work across different agent runtimes without coupling domain code to one framework.

## Role in `ai-automation-infra-demo`

```text
User / n8n event
      ↓
Agent Interop Runtime
      ↓ route / handoff / shared session
OpenAI-style agent ↔ LangGraph-style agent
      ↓
MCP tools through the policy gateway
```

## Demo responsibilities

- start one session from an inbound automation event
- run an initial triage/classification agent
- hand off to a second agent backed by another runtime adapter
- preserve conversation/session state across the runtime boundary
- expose MCP tools through the runtime-neutral tool provider
- enforce session step/token/cost budgets
- persist the session using the PostgreSQL session store

## Stable integration surface

The integration repository imports public contracts only: `AgentSpec`, `InteropRuntime`, adapters, session stores, tool registry and handoff primitives. Demo code must not depend on framework-specific internals.

## Reference scenario

The first agent classifies a customer refund request and hands it to a finance agent. The finance agent prepares the protected tool call, but execution still travels through `mcp-policy-gateway` rather than calling the downstream service directly.

This makes the demo prove both portability and security:

```text
Runtime A → portable handoff → Runtime B → MCP Policy Gateway → tool
```

## Boundary rule

Adapter contracts, handoffs, session persistence, provider abstractions and portability rules belong in `agent-interop-runtime`. The demo composes them but does not fork or duplicate them.
