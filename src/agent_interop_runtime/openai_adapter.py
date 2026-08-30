from __future__ import annotations

from typing import Any

from .core import AdapterCapabilities, AgentSpec, RunRequest, RunResult, RuntimeEvent


class OpenAIAgentsAdapter:
    """Adapter for the OpenAI Agents SDK with dependency injection for tests/custom runners."""

    name = "openai-agents"

    def __init__(self, *, tools: dict[str, object] | None = None, runner=None, agent_factory=None) -> None:
        self.tools = tools or {}
        self._runner = runner
        self._agent_factory = agent_factory

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(streaming=True, tools=True, handoffs=True, structured_output=True)

    def _sdk(self):
        runner = self._runner
        factory = self._agent_factory
        if runner is None or factory is None:
            try:
                from agents import Agent, Runner
            except ImportError as exc:
                raise RuntimeError("install agent-interop-runtime[openai] to use OpenAIAgentsAdapter") from exc
            runner = runner or Runner
            factory = factory or Agent
        return runner, factory

    def _build_agent(self, spec: AgentSpec):
        _, factory = self._sdk()
        missing = [name for name in spec.tools if name not in self.tools]
        if missing:
            raise ValueError(f"OpenAI adapter is missing registered tools: {', '.join(missing)}")
        return factory(
            name=spec.name,
            instructions=spec.instructions,
            model=spec.model,
            tools=[self.tools[name] for name in spec.tools],
        )

    def run(self, spec: AgentSpec, request: RunRequest) -> RunResult:
        runner, _ = self._sdk()
        agent = self._build_agent(spec)
        kwargs: dict[str, Any] = {"max_turns": spec.policy.max_steps}
        if request.context:
            kwargs["context"] = request.context
        result = runner.run_sync(agent, request.input, **kwargs)
        items = list(getattr(result, "new_items", []) or [])
        tool_calls = self._tool_calls(items)
        output = getattr(result, "final_output", result)
        metadata: dict[str, object] = {"model": spec.model}
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
        if usage is not None:
            for attr in ("input_tokens", "output_tokens", "total_tokens", "requests"):
                value = getattr(usage, attr, None)
                if value is not None:
                    metadata[attr] = value
        return RunResult(
            output=str(output),
            runtime=self.name,
            steps=max(1, len(items)),
            tool_calls=tool_calls,
            metadata=metadata,
        )

    async def astream(self, spec: AgentSpec, request: RunRequest):
        runner, _ = self._sdk()
        agent = self._build_agent(spec)
        kwargs: dict[str, Any] = {"max_turns": spec.policy.max_steps}
        if request.context:
            kwargs["context"] = request.context
        result = runner.run_streamed(agent, request.input, **kwargs)
        async for event in result.stream_events():
            event_type = str(getattr(event, "type", "event"))
            name = str(getattr(event, "name", ""))
            yield RuntimeEvent(type=event_type, name=name, data={"runtime": self.name})

    @staticmethod
    def _tool_calls(items) -> tuple[str, ...]:
        names: list[str] = []
        for item in items:
            item_type = str(getattr(item, "type", ""))
            if "tool_call" not in item_type:
                continue
            raw = getattr(item, "raw_item", item)
            name = getattr(raw, "name", None)
            if name:
                names.append(str(name))
        return tuple(names)
