from agent_interop_runtime import AgentSpec, InteropRuntime, MockAdapter, RuntimePolicy

runtime = InteropRuntime()
runtime.register(MockAdapter())

agent = AgentSpec(
    name="research-agent",
    instructions="Research the request and return a concise answer.",
    model="mock-model",
    tools=("search",),
    policy=RuntimePolicy(max_steps=5, allowed_tools=("search",)),
)

result = runtime.run("mock", agent, "Summarize the latest release notes")
print(result)
