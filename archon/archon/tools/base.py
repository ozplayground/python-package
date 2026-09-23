"""Abstract base tool interface."""
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field

from archon.tools.result import ToolExecutionResult


class BaseTool(ABC, BaseModel):
    """Abstract base class for all tools executable by Archon agents."""

    name: str
    description: str = ""
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolExecutionResult:
        """Execute the tool with given arguments and return a ToolExecutionResult."""

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool metadata to standard OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema or {
                    "type": "object",
                    "properties": {},
                },
            },
        }
