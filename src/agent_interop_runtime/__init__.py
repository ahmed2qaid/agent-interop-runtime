from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class RuntimePolicy:
    max_steps: int = 20
    max_cost_usd: float | None = None
    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentSpec:
    name: str
    instructions: str
    model: str
    tools: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    policy: RuntimePolicy = field(default_factory=RuntimePolicy)


@dataclass(frozen=True)
class RunRequest:
    input: str
    context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    output: str
    runtime: str
    steps: int = 1
    tool_calls: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


class RuntimeAdapter(Protocol):
    name: str

    def run(self, spec: AgentSpec, request: RunRequest) -> RunResult: ...


class MockAdapter:
    name = "mock"

    def run(self, spec: AgentSpec, request: RunRequest) -> RunResult:
        selected_tools = tuple(spec.tools[:1])
        return RunResult(
            output=f"[{spec.name}] {request.input}",
            runtime=self.name,
            steps=1,
            tool_calls=selected_tools,
            metadata={"model": spec.model, "deterministic": True},
        )


class InteropRuntime:
    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {}

    def register(self, adapter: RuntimeAdapter) -> None:
        if not adapter.name:
            raise ValueError("adapter name must not be empty")
        self._adapters[adapter.name] = adapter

    def adapters(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def run(
        self,
        adapter_name: str,
        spec: AgentSpec,
        input_text: str,
        *,
        context: dict[str, object] | None = None,
    ) -> RunResult:
        self._validate_spec(spec)
        try:
            adapter = self._adapters[adapter_name]
        except KeyError as exc:
            raise KeyError(f"runtime adapter is not registered: {adapter_name}") from exc

        result = adapter.run(spec, RunRequest(input=input_text, context=context or {}))
        if result.steps > spec.policy.max_steps:
            raise RuntimeError(
                f"adapter exceeded max_steps policy: {result.steps} > {spec.policy.max_steps}"
            )
        return result

    @staticmethod
    def _validate_spec(spec: AgentSpec) -> None:
        if not spec.name.strip():
            raise ValueError("agent name must not be empty")
        if not spec.instructions.strip():
            raise ValueError("agent instructions must not be empty")
        if spec.policy.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if spec.policy.allowed_tools:
            disallowed = sorted(set(spec.tools) - set(spec.policy.allowed_tools))
            if disallowed:
                raise ValueError(f"agent declares tools forbidden by policy: {', '.join(disallowed)}")


__all__ = [
    "AgentSpec",
    "InteropRuntime",
    "MockAdapter",
    "RunRequest",
    "RunResult",
    "RuntimeAdapter",
    "RuntimePolicy",
]
