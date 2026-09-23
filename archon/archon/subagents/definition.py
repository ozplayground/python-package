"""Subagent definitions, requests, and result models."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubagentDefinition(BaseModel):
    """Specification of a specialized subagent."""

    name: str
    description: str = ""
    system_prompt: str = ""
    allowed_tools: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    max_turns: int = Field(default=10, ge=1)
    timeout_seconds: float = Field(default=120.0, gt=0.0)

    model_config = ConfigDict(frozen=True)


class SubagentRequest(BaseModel):
    """Invocation request for dispatching a subagent."""

    subagent_name: str
    prompt: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[float] = None

    model_config = ConfigDict(frozen=True)


class SubagentResult(BaseModel):
    """Outcome of a subagent execution."""

    subagent_name: str
    is_success: bool = True
    output: str = ""
    error: Optional[str] = None
    is_timeout: bool = False
    turns_used: int = 0
    duration_ms: float = 0.0

    model_config = ConfigDict(frozen=True)
