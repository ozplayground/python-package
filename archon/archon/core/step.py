"""Step execution result model."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StepResult(BaseModel):
    """Result of an agent turn, containing text output and optional tool calls."""

    text: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    is_complete: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
