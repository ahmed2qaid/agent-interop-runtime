# Execution Roadmap

## v0.1 — Neutral runtime contract

- [x] `AgentSpec`, `RunRequest`, and `RunResult` contracts
- [x] adapter protocol and registry
- [x] runtime policy validation
- [x] deterministic mock adapter
- [x] conformance tests and CI

## v0.2 — Real adapters

- [x] OpenAI Agents SDK adapter
- [x] LangGraph compiled-graph adapter
- [x] adapter capability discovery
- [x] normalized streaming event contract
- [x] structured tool-call extraction
- [x] optional framework dependencies

## v0.3 — Multi-agent interoperability

- [x] runtime-neutral handoff contract
- [x] shared conversation/session state
- [x] agent route registry
- [x] framework-crossing handoffs (for example OpenAI → LangGraph)
- [x] portable handoff envelope for protocol experiments
- [x] runtime-neutral MCP tool discovery/call provider
- [x] tests proving session history survives runtime boundaries

Exit criteria: two agents backed by different runtime adapters can share one session and hand off work through a portable contract without importing either framework into application/domain code.

## v0.4 — Persistence and portability

- [x] PostgreSQL session store with lazy `psycopg` integration
- [x] portable runtime-neutral checkpoint format
- [x] runtime-neutral tool registry and callable tool contract
- [x] model-provider request/response abstraction and provider registry
- [x] session-level cost, token, and step budget enforcement
- [x] serialization tests proving session/checkpoint portability

Exit criteria: session state, tools, model providers, and execution budgets can survive framework boundaries without making domain code depend on OpenAI Agents, LangGraph, or a specific model vendor.

## v1.0

- at least four production adapters
- compatibility matrix
- conformance suite for third-party adapter authors
- stable event model
- benchmark suite for runtime portability overhead
