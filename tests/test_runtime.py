import unittest

from agent_interop_runtime import AgentSpec, InteropRuntime, MockAdapter, RuntimePolicy


class RuntimeTests(unittest.TestCase):
    def test_one_spec_runs_through_registered_adapter(self) -> None:
        runtime = InteropRuntime()
        runtime.register(MockAdapter())
        spec = AgentSpec(
            name="agent",
            instructions="Answer",
            model="mock",
            tools=("search",),
            policy=RuntimePolicy(max_steps=3, allowed_tools=("search",)),
        )

        result = runtime.run("mock", spec, "hello")
        self.assertEqual(result.runtime, "mock")
        self.assertEqual(result.tool_calls, ("search",))
        self.assertIn("hello", result.output)

    def test_policy_rejects_disallowed_tool(self) -> None:
        runtime = InteropRuntime()
        runtime.register(MockAdapter())
        spec = AgentSpec(
            name="agent",
            instructions="Answer",
            model="mock",
            tools=("delete_database",),
            policy=RuntimePolicy(allowed_tools=("search",)),
        )

        with self.assertRaises(ValueError):
            runtime.run("mock", spec, "hello")

    def test_unknown_adapter_is_explicit(self) -> None:
        runtime = InteropRuntime()
        spec = AgentSpec(name="agent", instructions="Answer", model="mock")
        with self.assertRaises(KeyError):
            runtime.run("missing", spec, "hello")


if __name__ == "__main__":
    unittest.main()
