# Agent Interop Runtime

Define an agent once, then execute it through different agent frameworks using explicit adapters instead of coupling application code to one vendor/runtime.

```text
                AgentSpec
                   │
        ┌──────────┼──────────┐
        ↓          ↓          ↓
 OpenAI Agents  LangGraph   future adapters
        │          │
        └────── RunResult / RuntimeEvent ──────┘
```

## v0.2

- framework-neutral `AgentSpec`, `RunRequest`, `RunResult`
- runtime policy validation
- adapter registry
- adapter capability discovery
- normalized `RuntimeEvent` contract
- real OpenAI Agents SDK adapter
- real LangGraph compiled-graph adapter
- structured tool-call extraction
- OpenAI streamed-event adapter
- LangGraph update streaming
- optional framework dependencies; core remains dependency-free
- deterministic conformance tests

## Define once

```python
from agent_interop_runtime import AgentSpec, RuntimePolicy

spec = AgentSpec(
    name="researcher",
    instructions="Research the question and cite evidence.",
    model="gpt-5",
    tools=("search",),
    policy=RuntimePolicy(max_steps=10, allowed_tools=("search",)),
)
```

## OpenAI Agents SDK

```bash
pip install -e '.[openai]'
```

```python
adapter = OpenAIAgentsAdapter(tools={"search": search_tool})
runtime.register(adapter)
result = runtime.run("openai-agents", spec, "Compare two approaches")
```

The adapter constructs an SDK `Agent`, passes the neutral `max_steps` policy as `max_turns`, and converts SDK output/tool-call metadata back into `RunResult`.

## LangGraph

```bash
pip install -e '.[langgraph]'
```

A LangGraph application supplies a graph factory because graph state schemas are application-specific:

```python
adapter = LangGraphAdapter(lambda spec: compiled_graph)
runtime.register(adapter)
result = runtime.run("langgraph", spec, "Compare two approaches")
```

`input_builder` and `output_parser` are replaceable when your graph uses a custom state schema.

## Why not fork a framework?

Interoperability is only useful if the core remains neutral. OpenAI Agents and LangGraph are optional edges around the same contract; later adapters can target CrewAI, Microsoft Agent Framework, Google ADK, MCP, or A2A without rewriting domain code.

See [ROADMAP.md](ROADMAP.md).

## License

MIT.
