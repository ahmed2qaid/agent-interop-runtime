# Execution Roadmap

## v0.1 — Neutral runtime contract

- [x] `AgentSpec`, `RunRequest`, and `RunResult` contracts
- [x] adapter protocol and registry
- [x] runtime policy validation
- [x] deterministic mock adapter
- [x] conformance tests and CI

Exit criteria: an application can define one agent contract and execute it through a registered adapter without importing that adapter in domain code.

## v0.2 — Real adapters

- OpenAI Agents SDK adapter
- LangGraph adapter
- adapter capability discovery
- streaming event contract
- structured tool call events

## v0.3 — Multi-agent interoperability

- handoff contract
- shared conversation/session state
- framework-crossing handoffs
- MCP tool provider adapter
- A2A interoperability experiments

## v0.4 — Persistence and portability

- Postgres session store
- portable checkpoints
- runtime-neutral tool registry
- model-provider abstraction
- policy and budget enforcement

## v1.0

- at least four production adapters
- compatibility matrix
- conformance suite for third-party adapter authors
- stable event model
- benchmark suite for runtime portability overhead
