"""Session-isolated tool registry."""
from typing import Any, Callable, Dict, Iterator, List, Optional
from archon.tools.base import BaseTool
from archon.tools.decorator import FunctionTool


class ToolRegistry:
    """Registry managing available tools for an agent session."""

    def __init__(self, tools: Optional[Dict[str, BaseTool]] = None) -> None:
        self._tools: Dict[str, BaseTool] = dict(tools or {})

    def register(self, tool: BaseTool) -> None:
        """Register a BaseTool instance."""
        self._tools[tool.name] = tool

    def register_func(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> BaseTool:
        """Wrap and register a Python function as a tool."""
        wrapped = FunctionTool(func, name=name, description=description)
        self.register(wrapped)
        return wrapped

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI-compatible function calling schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def clone(self) -> "ToolRegistry":
        """Create an independent copy of this registry for session isolation."""
        return ToolRegistry(tools=dict(self._tools))

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self) -> Iterator[str]:
        return iter(self._tools)

    def __len__(self) -> int:
        return len(self._tools)
