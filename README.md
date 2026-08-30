# Agent Interop Runtime

A framework-neutral runtime contract for AI agents.

Define an agent once, then execute it through pluggable runtime adapters instead of coupling application code to one agent framework.

## Core idea

```text
AgentSpec
   ↓
Interop Runtime
   ↓
Adapter Registry
   ├── OpenAI Agents
   ├── LangGraph
   ├── CrewAI
   ├── Microsoft Agent Framework
   └── Google ADK
```

v0.1 ships the framework-neutral contract, adapter registry, policy checks, and a deterministic reference adapter used by tests and examples.

## Quick start

```python
from agent_interop_runtime import AgentSpec, InteropRuntime, MockAdapter

runtime = InteropRuntime()
runtime.register(MockAdapter())

spec = AgentSpec(
    name="research-agent",
    instructions="Research the request and return a concise answer.",
    model="mock-model",
    tools=("search",),
)

result = runtime.run("mock", spec, "What changed?")
print(result.output)
```

## Design principles

- framework-neutral public contract
- explicit capabilities instead of hidden magic
- deterministic adapter conformance tests
- policy limits for steps, tools, and cost metadata
- adapters remain isolated from application code
- MCP and A2A are protocol integrations, not hard-coded runtime assumptions

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Status

v0.1 foundation.

## License

MIT.