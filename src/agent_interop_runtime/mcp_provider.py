from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class MCPClientLike(Protocol):
    async def list_tools(self): ...
    async def call_tool(self, name: str, arguments: dict): ...


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    source: str = "mcp"


class MCPToolProvider:
    """Normalize MCP tool discovery/calls without coupling the core runtime to the MCP SDK."""

    def __init__(self, client: MCPClientLike, *, prefix: str = "") -> None:
        self.client = client
        self.prefix = prefix.strip()
        self._raw_by_exposed: dict[str, str] = {}

    async def discover(self) -> tuple[ToolDefinition, ...]:
        response = await self.client.list_tools()
        tools = getattr(response, "tools", response)
        definitions: list[ToolDefinition] = []
        for tool in tools or []:
            raw_name = str(getattr(tool, "name", "") or (tool.get("name") if isinstance(tool, dict) else ""))
            if not raw_name:
                continue
            exposed = f"{self.prefix}__{raw_name}" if self.prefix else raw_name
            self._raw_by_exposed[exposed] = raw_name
            description = getattr(tool, "description", "")
            schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
            if isinstance(tool, dict):
                description = tool.get("description", description)
                schema = tool.get("inputSchema", tool.get("input_schema", schema))
            definitions.append(
                ToolDefinition(
                    name=exposed,
                    description=str(description or ""),
                    input_schema=dict(schema or {}),
                )
            )
        return tuple(definitions)

    async def call(self, name: str, arguments: dict | None = None):
        raw = self._raw_by_exposed.get(name)
        if raw is None:
            if self.prefix and name.startswith(self.prefix + "__"):
                raw = name.split("__", 1)[1]
            elif not self.prefix:
                raw = name
            else:
                raise KeyError(f"unknown MCP tool: {name}")
        return await self.client.call_tool(raw, arguments or {})
