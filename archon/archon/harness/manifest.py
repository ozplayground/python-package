"""Normalized immutable harness manifest snapshot."""
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field

from archon.skills.definition import SkillDefinition
from archon.subagents.definition import SubagentDefinition


class HarnessManifest(BaseModel):
    """Immutable snapshot of compiled harness governance."""

    constitution: str = ""
    rules: Dict[str, str] = Field(default_factory=dict)
    skills: Dict[str, SkillDefinition] = Field(default_factory=dict)
    subagents: Dict[str, SubagentDefinition] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
