from __future__ import annotations

import unittest

from agent_interop_runtime.handoff import ConversationTurn, SessionState
from agent_interop_runtime.portability import (
    BudgetExceeded,
    BudgetPolicy,
    BudgetTracker,
    ModelProviderRegistry,
    ModelRequest,
    ModelResponse,
    PortableCheckpoint,
    ToolRegistry,
    ToolSpec,
)
from agent_interop_runtime.postgres_session import session_from_dict, session_to_dict


class EchoProvider:
    name = "echo"

    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            output=request.input.upper(),
            provider=self.name,
            model=request.model,
            input_tokens=3,
            output_tokens=2,
            cost_usd=0.01,
        )


class PortabilityTests(unittest.TestCase):
    def test_portable_checkpoint_roundtrip(self):
        state = SessionState(
            "s1",
            values={"customer": "C-1"},
            turns=[ConversationTurn("assistant", "done", agent="a", runtime="openai")],
        )
        checkpoint = PortableCheckpoint.from_session(state, runtime="openai", adapter_state={"cursor": 2})
        restored = PortableCheckpoint.from_dict(checkpoint.to_dict()).restore_session()
        self.assertEqual(restored.session_id, "s1")
        self.assertEqual(restored.values["customer"], "C-1")
        self.assertEqual(restored.turns[0].runtime, "openai")

    def test_runtime_neutral_tool_registry(self):
        tools = ToolRegistry()
        tools.register(
            ToolSpec("sum", "Add two values", {"type": "object"}),
            lambda args: int(args["a"]) + int(args["b"]),
        )
        self.assertEqual(tools.call("sum", {"a": 2, "b": 5}), 7)
        self.assertEqual(tools.specs()[0].name, "sum")

    def test_model_provider_registry(self):
        providers = ModelProviderRegistry()
        providers.register(EchoProvider())
        result = providers.generate("echo", ModelRequest(model="demo", input="hello"))
        self.assertEqual(result.output, "HELLO")
        self.assertEqual(result.provider, "echo")

    def test_budget_tracker_blocks_overspend_before_mutating_totals(self):
        tracker = BudgetTracker(BudgetPolicy(max_cost_usd=0.05, max_tokens=10, max_steps=4))
        tracker.record(cost_usd=0.02, tokens=4, steps=1)
        with self.assertRaises(BudgetExceeded):
            tracker.record(cost_usd=0.04, tokens=1, steps=1)
        self.assertEqual(tracker.cost_usd, 0.02)
        self.assertEqual(tracker.tokens, 4)

    def test_session_serialization_for_postgres_store(self):
        state = SessionState(
            "session-9",
            values={"stage": 2},
            turns=[ConversationTurn("user", "hi"), ConversationTurn("assistant", "hello", agent="support")],
        )
        restored = session_from_dict(session_to_dict(state))
        self.assertEqual(restored.session_id, state.session_id)
        self.assertEqual(restored.values, state.values)
        self.assertEqual([turn.content for turn in restored.turns], ["hi", "hello"])


if __name__ == "__main__":
    unittest.main()
