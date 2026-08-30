from __future__ import annotations

import json
from typing import Any

from .handoff import ConversationTurn, SessionState


class PostgresSessionStore:
    """PostgreSQL-backed SessionStore.

    Pass a DB-API compatible PostgreSQL connection. `from_dsn()` lazily imports
    psycopg so the core package remains dependency-light.
    """

    def __init__(self, connection: Any, *, initialize: bool = True) -> None:
        self.connection = connection
        if initialize:
            self.initialize()

    @classmethod
    def from_dsn(cls, dsn: str, *, initialize: bool = True) -> "PostgresSessionStore":
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("install agent-interop-runtime[postgres] to use PostgresSessionStore.from_dsn") from exc
        return cls(psycopg.connect(dsn), initialize=initialize)

    def initialize(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_interop_sessions (
                    session_id TEXT PRIMARY KEY,
                    state JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        self.connection.commit()

    def load(self, session_id: str) -> SessionState:
        if not session_id:
            raise ValueError("session_id must not be empty")
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT state FROM agent_interop_sessions WHERE session_id = %s", (session_id,))
            row = cursor.fetchone()
        if row is None:
            return SessionState(session_id=session_id)
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return session_from_dict(dict(payload))

    def save(self, state: SessionState) -> None:
        payload = json.dumps(session_to_dict(state), ensure_ascii=False, separators=(",", ":"))
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_interop_sessions(session_id, state, updated_at)
                VALUES (%s, %s::jsonb, now())
                ON CONFLICT(session_id) DO UPDATE SET state = EXCLUDED.state, updated_at = now()
                """,
                (state.session_id, payload),
            )
        self.connection.commit()

    def close(self) -> None:
        close = getattr(self.connection, "close", None)
        if callable(close):
            close()


def session_to_dict(state: SessionState) -> dict[str, object]:
    return {
        "session_id": state.session_id,
        "values": dict(state.values),
        "turns": [
            {
                "role": turn.role,
                "content": turn.content,
                "agent": turn.agent,
                "runtime": turn.runtime,
                "metadata": dict(turn.metadata),
            }
            for turn in state.turns
        ],
    }


def session_from_dict(data: dict) -> SessionState:
    session_id = str(data.get("session_id", "")).strip()
    if not session_id:
        raise ValueError("persisted session requires session_id")
    raw_turns = data.get("turns", [])
    if not isinstance(raw_turns, list):
        raise ValueError("persisted session turns must be a list")
    turns: list[ConversationTurn] = []
    for item in raw_turns:
        if not isinstance(item, dict):
            raise ValueError("persisted session turn must be an object")
        turns.append(
            ConversationTurn(
                role=str(item.get("role", "")),
                content=str(item.get("content", "")),
                agent=str(item.get("agent", "")),
                runtime=str(item.get("runtime", "")),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return SessionState(session_id=session_id, values=dict(data.get("values", {})), turns=turns)
