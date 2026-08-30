from __future__ import annotations

from collections.abc import Callable, Iterator

from .core import AdapterCapabilities, AgentSpec, RunRequest, RunResult, RuntimeEvent


class LangGraphAdapter:
    """Run a framework-neutral AgentSpec through a user-supplied compiled LangGraph graph."""

    name = "langgraph"

    def __init__(
        self,
        graph_factory: Callable[[AgentSpec], object],
        *,
        input_builder: Callable[[AgentSpec, RunRequest], object] | None = None,
        output_parser: Callable[[object], str] | None = None,
    ) -> None:
        self.graph_factory = graph_factory
        self.input_builder = input_builder or self._default_input
        self.output_parser = output_parser or self._default_output

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=True, tools=True, persistent_state=True)

    def run(self, spec: AgentSpec, request: RunRequest) -> RunResult:
        graph = self.graph_factory(spec)
        if not hasattr(graph, "invoke"):
            raise TypeError("LangGraph factory must return an object with invoke()")
        payload = self.input_builder(spec, request)
        result = graph.invoke(payload)
        tool_calls = self._extract_tool_calls(result)
        return RunResult(
            output=self.output_parser(result),
            runtime=self.name,
            steps=max(1, self._estimate_steps(result)),
            tool_calls=tool_calls,
            metadata={"model": spec.model, "graph_type": type(graph).__name__},
        )

    def stream(self, spec: AgentSpec, request: RunRequest) -> Iterator[RuntimeEvent]:
        graph = self.graph_factory(spec)
        if not hasattr(graph, "stream"):
            raise TypeError("LangGraph factory must return an object with stream()")
        payload = self.input_builder(spec, request)
        for chunk in graph.stream(payload, stream_mode="updates"):
            if isinstance(chunk, dict):
                for node, data in chunk.items():
                    yield RuntimeEvent(type="graph.update", name=str(node), data={"value": data})
            else:
                yield RuntimeEvent(type="graph.update", data={"value": chunk})

    @staticmethod
    def _default_input(spec: AgentSpec, request: RunRequest) -> dict:
        return {
            "messages": [{"role": "user", "content": request.input}],
            "interop": {
                "agent_name": spec.name,
                "instructions": spec.instructions,
                "model": spec.model,
                "tools": list(spec.tools),
                "context": request.context,
            },
        }

    @staticmethod
    def _default_output(result: object) -> str:
        if isinstance(result, dict):
            if isinstance(result.get("output"), str):
                return result["output"]
            messages = result.get("messages")
            if isinstance(messages, list) and messages:
                last = messages[-1]
                if isinstance(last, dict):
                    return str(last.get("content", last))
                content = getattr(last, "content", None)
                if content is not None:
                    return str(content)
        return str(result)

    @staticmethod
    def _estimate_steps(result: object) -> int:
        if isinstance(result, dict):
            messages = result.get("messages")
            if isinstance(messages, list):
                return len(messages)
        return 1

    @staticmethod
    def _extract_tool_calls(result: object) -> tuple[str, ...]:
        if not isinstance(result, dict):
            return ()
        messages = result.get("messages")
        if not isinstance(messages, list):
            return ()
        names: list[str] = []
        for message in messages:
            calls = message.get("tool_calls", []) if isinstance(message, dict) else getattr(message, "tool_calls", [])
            for call in calls or []:
                if isinstance(call, dict):
                    name = call.get("name") or (call.get("function") or {}).get("name")
                else:
                    name = getattr(call, "name", None)
                if name:
                    names.append(str(name))
        return tuple(names)
