from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from .core import RunResult
from .handoff import ConversationTurn, SessionState


CHECKPOINT_FORMAT = "agent-interop-checkpoint/v1"


@dataclass(frozen=True)
class PortableCheckpoint:
    session_id: str
    runtime: str
    values: dict[str, object]
    turns: tuple[ConversationTurn, ...]
    adapter_state: dict[str, object] = field(default_factory=dict)
    format: str = CHECKPOINT_FORMAT

    @classmethod
    def from_session(
        cls,
        state: SessionState,
        *,
        runtime: str,
        adapter_state: dict[str, object] | None = None,
    ) -> "PortableCheckpoint":
        return cls(
            session_id=state.session_id,
            runtime=runtime,
            values=dict(state.values),
            turns=tuple(state.turns),
            adapter_state=dict(adapter_state or {}),
        )

    def restore_session(self) -> SessionState:
        if self.format != CHECKPOINT_FORMAT:
            raise ValueError(f"unsupported checkpoint format: {self.format}")
        return SessionState(
            session_id=self.session_id,
            values=dict(self.values),
            turns=list(self.turns),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "session_id": self.session_id,
            "runtime": self.runtime,
            "values": dict(self.values),
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "agent": turn.agent,
                    "runtime": turn.runtime,
                    "metadata": dict(turn.metadata),
                }
                for turn in self.turns
            ],
            "adapter_state": dict(self.adapter_state),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortableCheckpoint":
        if data.get("format") != CHECKPOINT_FORMAT:
            raise ValueError("unsupported portable checkpoint format")
        session_id = str(data.get("session_id", "")).strip()
        runtime = str(data.get("runtime", "")).strip()
        if not session_id or not runtime:
            raise ValueError("checkpoint session_id and runtime are required")
        raw_turns = data.get("turns", [])
        if not isinstance(raw_turns, list):
            raise ValueError("checkpoint turns must be a list")
        turns = []
        for item in raw_turns:
            if not isinstance(item, dict):
                raise ValueError("checkpoint turn must be an object")
            turns.append(
                ConversationTurn(
                    role=str(item.get("role", "")),
                    content=str(item.get("content", "")),
                    agent=str(item.get("agent", "")),
                    runtime=str(item.get("runtime", "")),
                    metadata=dict(item.get("metadata", {})),
                )
            )
        return cls(
            session_id=session_id,
            runtime=runtime,
            values=dict(data.get("values", {})),
            turns=tuple(turns),
            adapter_state=dict(data.get("adapter_state", {})),
        )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str = ""
    input_schema: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


ToolHandler = Callable[[dict[str, object]], object]


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if not spec.name.strip():
            raise ValueError("tool name must not be empty")
        if spec.name in self._specs:
            raise ValueError(f"tool already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(self._specs[name] for name in sorted(self._specs))

    def call(self, name: str, arguments: dict[str, object] | None = None) -> object:
        try:
            handler = self._handlers[name]
        except KeyError as exc:
            raise KeyError(f"tool is not registered: {name}") from exc
        return handler(dict(arguments or {}))


@dataclass(frozen=True)
class ModelRequest:
    model: str
    input: str
    instructions: str = ""
    context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    output: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


class ModelProvider(Protocol):
    name: str
    def generate(self, request: ModelRequest) -> ModelResponse: ...


class ModelProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        if not provider.name:
            raise ValueError("model provider name must not be empty")
        self._providers[provider.name] = provider

    def generate(self, provider: str, request: ModelRequest) -> ModelResponse:
        try:
            implementation = self._providers[provider]
        except KeyError as exc:
            raise KeyError(f"model provider is not registered: {provider}") from exc
        return implementation.generate(request)

    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


@dataclass(frozen=True)
class BudgetPolicy:
    max_cost_usd: float | None = None
    max_tokens: int | None = None
    max_steps: int | None = None


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetTracker:
    policy: BudgetPolicy
    cost_usd: float = 0.0
    tokens: int = 0
    steps: int = 0

    def record(self, *, cost_usd: float = 0.0, tokens: int = 0, steps: int = 0) -> None:
        next_cost = self.cost_usd + float(cost_usd)
        next_tokens = self.tokens + int(tokens)
        next_steps = self.steps + int(steps)
        if self.policy.max_cost_usd is not None and next_cost > self.policy.max_cost_usd:
            raise BudgetExceeded(f"session cost budget exceeded: {next_cost} > {self.policy.max_cost_usd}")
        if self.policy.max_tokens is not None and next_tokens > self.policy.max_tokens:
            raise BudgetExceeded(f"session token budget exceeded: {next_tokens} > {self.policy.max_tokens}")
        if self.policy.max_steps is not None and next_steps > self.policy.max_steps:
            raise BudgetExceeded(f"session step budget exceeded: {next_steps} > {self.policy.max_steps}")
        self.cost_usd = next_cost
        self.tokens = next_tokens
        self.steps = next_steps

    def record_result(self, result: RunResult) -> None:
        raw_tokens = result.metadata.get("total_tokens")
        if raw_tokens is None:
            raw_tokens = int(result.metadata.get("input_tokens", 0) or 0) + int(result.metadata.get("output_tokens", 0) or 0)
        self.record(
            cost_usd=float(result.metadata.get("cost_usd", 0.0) or 0.0),
            tokens=int(raw_tokens or 0),
            steps=result.steps,
        )

    def snapshot(self) -> dict[str, object]:
        return {"cost_usd": self.cost_usd, "tokens": self.tokens, "steps": self.steps}
