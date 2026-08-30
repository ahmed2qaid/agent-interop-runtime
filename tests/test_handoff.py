import asyncio
import unittest

from agent_interop_runtime import (
    AdapterCapabilities,
    AgentSpec,
    HandoffRequest,
    HandoffRouter,
    InteropRuntime,
    MCPToolProvider,
    MemorySessionStore,
    RunResult,
)


class PrefixAdapter:
    def __init__(self, name):
        self.name = name

    def capabilities(self):
        return AdapterCapabilities(tools=True, handoffs=True)

    def run(self, spec, request):
        handoff = request.context.get("handoff")
        marker = "handoff" if handoff else "direct"
        return RunResult(
            output=f"{self.name}:{spec.name}:{marker}:{request.input}",
            runtime=self.name,
            metadata={"session_id": request.context.get("session_id")},
        )


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = "demo"
        self.inputSchema = {"type": "object"}


class FakeList:
    def __init__(self):
        self.tools = [FakeTool("search")]


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    async def list_tools(self):
        return FakeList()

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"ok": True}


class HandoffTests(unittest.TestCase):
    def make_router(self):
        runtime = InteropRuntime()
        runtime.register(PrefixAdapter("openai"))
        runtime.register(PrefixAdapter("langgraph"))
        sessions = MemorySessionStore()
        router = HandoffRouter(runtime, sessions=sessions)
        router.register_agent("researcher", "openai", AgentSpec("researcher", "research", "model-a"))
        router.register_agent("writer", "langgraph", AgentSpec("writer", "write", "model-b"))
        return router, sessions

    def test_cross_framework_handoff_preserves_session(self):
        router, sessions = self.make_router()
        first = router.run("researcher", "find facts", session_id="s-1")
        self.assertEqual(first.runtime, "openai")

        handed = router.handoff(
            HandoffRequest(
                source_agent="researcher",
                target_agent="writer",
                input="write the brief",
                reason="research complete",
                context={"facts": ["a", "b"]},
            ),
            session_id="s-1",
        )
        self.assertEqual(handed.source_runtime, "openai")
        self.assertEqual(handed.target_runtime, "langgraph")
        self.assertIn("handoff", handed.result.output)

        state = sessions.load("s-1")
        self.assertEqual([turn.role for turn in state.turns], ["user", "assistant", "handoff", "assistant"])
        self.assertEqual(state.turns[2].metadata["target_agent"], "writer")

    def test_portable_handoff_context_reaches_target(self):
        router, _ = self.make_router()
        result = router.handoff(
            HandoffRequest("researcher", "writer", "continue", reason="specialist needed"),
            session_id="s-2",
        )
        self.assertEqual(result.result.metadata["session_id"], "s-2")

    def test_mcp_provider_normalizes_discovery_and_calls(self):
        client = FakeMCPClient()
        provider = MCPToolProvider(client, prefix="crm")
        tools = asyncio.run(provider.discover())
        self.assertEqual(tools[0].name, "crm__search")
        result = asyncio.run(provider.call("crm__search", {"q": "Ahmed"}))
        self.assertTrue(result["ok"])
        self.assertEqual(client.calls, [("search", {"q": "Ahmed"})])


if __name__ == "__main__":
    unittest.main()
