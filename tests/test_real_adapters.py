import asyncio
import unittest

from agent_interop_runtime import AgentSpec, InteropRuntime, LangGraphAdapter, OpenAIAgentsAdapter, RunRequest


class FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeItem:
    type = "tool_call_item"

    class Raw:
        name = "search"

    raw_item = Raw()


class FakeOpenAIResult:
    final_output = "openai-result"
    new_items = [FakeItem()]
    context_wrapper = None


class FakeRunner:
    @staticmethod
    def run_sync(agent, input_text, **kwargs):
        assert agent.kwargs["name"] == "researcher"
        assert kwargs["max_turns"] == 5
        return FakeOpenAIResult()


class FakeGraph:
    def invoke(self, payload):
        return {
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "langgraph-result", "tool_calls": [{"name": "search"}]},
            ]
        }

    def stream(self, payload, stream_mode="updates"):
        yield {"research": {"done": True}}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.spec = AgentSpec(
            name="researcher",
            instructions="Research accurately",
            model="demo-model",
            tools=("search",),
            policy=__import__("agent_interop_runtime").RuntimePolicy(max_steps=5, allowed_tools=("search",)),
        )

    def test_openai_adapter_maps_neutral_spec(self):
        runtime = InteropRuntime()
        runtime.register(OpenAIAgentsAdapter(tools={"search": object()}, runner=FakeRunner, agent_factory=FakeAgent))
        result = runtime.run("openai-agents", self.spec, "hello")
        self.assertEqual(result.output, "openai-result")
        self.assertEqual(result.tool_calls, ("search",))
        self.assertTrue(runtime.capabilities("openai-agents").streaming)

    def test_langgraph_adapter_maps_neutral_spec(self):
        adapter = LangGraphAdapter(lambda spec: FakeGraph())
        runtime = InteropRuntime()
        runtime.register(adapter)
        result = runtime.run("langgraph", self.spec, "hello")
        self.assertEqual(result.output, "langgraph-result")
        self.assertEqual(result.tool_calls, ("search",))
        events = list(adapter.stream(self.spec, RunRequest("hello")))
        self.assertEqual(events[0].name, "research")


if __name__ == "__main__":
    unittest.main()
