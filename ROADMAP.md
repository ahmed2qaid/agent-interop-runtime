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
- [x] adapter mapping tests

Exit criteria: the same `AgentSpec` can execute through two distinct real framework adapters while application/domain code depends only on the neutral contract.

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
