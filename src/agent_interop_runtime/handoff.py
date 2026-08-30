from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from .core import AgentSpec, InteropRuntime, RunResult


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str
    agent: str = ""
    runtime: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class SessionState:
    session_id: str
    values: dict[str, object] = field(default_factory=dict)
    turns: list[ConversationTurn] = field(default_factory=list)


class SessionStore(Protocol):
    def load(self, session_id: str) -> SessionState: ...
    def save(self, state: SessionState) -> None: ...


class MemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def load(self, session_id: str) -> SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionState(session_id)
            self._sessions[session_id] = state
        return state

    def save(self, state: SessionState) -> None:
        self._sessions[state.session_id] = state


@dataclass(frozen=True)
class AgentRoute:
    name: str
    adapter: str
    spec: AgentSpec


@dataclass(frozen=True)
class HandoffRequest:
    source_agent: str
    target_agent: str
    input: str
    reason: str = ""
    context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class HandoffResult:
    session_id: str
    source_agent: str
    target_agent: str
    source_runtime: str
    target_runtime: str
    result: RunResult


@dataclass(frozen=True)
class PortableHandoffEnvelope:
    """Runtime-neutral handoff envelope; intentionally smaller than full A2A."""

    id: str
    session_id: str
    source_agent: str
    target_agent: str
    input: str
    reason: str
    context: dict[str, object]

    @classmethod
    def from_request(cls, request: HandoffRequest, session_id: str) -> "PortableHandoffEnvelope":
        return cls(
            id=str(uuid4()),
            session_id=session_id,
            source_agent=request.source_agent,
            target_agent=request.target_agent,
            input=request.input,
            reason=request.reason,
            context=dict(request.context),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "input": self.input,
            "reason": self.reason,
            "context": dict(self.context),
        }


class HandoffRouter:
    def __init__(self, runtime: InteropRuntime, *, sessions: SessionStore | None = None) -> None:
        self.runtime = runtime
        self.sessions = sessions or MemorySessionStore()
        self._routes: dict[str, AgentRoute] = {}

    def register_agent(self, name: str, adapter: str, spec: AgentSpec) -> None:
        if not name:
            raise ValueError("agent route name must not be empty")
        self._routes[name] = AgentRoute(name, adapter, spec)

    def run(self, agent: str, input_text: str, *, session_id: str, context: dict[str, object] | None = None) -> RunResult:
        route = self._route(agent)
        state = self.sessions.load(session_id)
        merged = {"session_id": session_id, "session": state.values, **(context or {})}
        state.turns.append(ConversationTurn("user", input_text, metadata={"target_agent": agent}))
        result = self.runtime.run(route.adapter, route.spec, input_text, context=merged)
        state.turns.append(ConversationTurn("assistant", result.output, agent=agent, runtime=result.runtime, metadata=result.metadata))
        self.sessions.save(state)
        return result

    def handoff(self, request: HandoffRequest, *, session_id: str) -> HandoffResult:
        source = self._route(request.source_agent)
        target = self._route(request.target_agent)
        state = self.sessions.load(session_id)
        envelope = PortableHandoffEnvelope.from_request(request, session_id)
        state.turns.append(
            ConversationTurn(
                "handoff",
                request.input,
                agent=request.source_agent,
                runtime=source.adapter,
                metadata={"target_agent": request.target_agent, "reason": request.reason, "envelope_id": envelope.id},
            )
        )
        merged = {
            "session_id": session_id,
            "session": state.values,
            "handoff": envelope.to_dict(),
            **request.context,
        }
        result = self.runtime.run(target.adapter, target.spec, request.input, context=merged)
        state.turns.append(
            ConversationTurn("assistant", result.output, agent=request.target_agent, runtime=result.runtime, metadata=result.metadata)
        )
        self.sessions.save(state)
        return HandoffResult(session_id, request.source_agent, request.target_agent, source.adapter, target.adapter, result)

    def _route(self, agent: str) -> AgentRoute:
        try:
            return self._routes[agent]
        except KeyError as exc:
            raise KeyError(f"agent route is not registered: {agent}") from exc
