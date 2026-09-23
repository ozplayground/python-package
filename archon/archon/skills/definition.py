"""Skill definition model."""
from pydantic import BaseModel, ConfigDict, Field


class SkillDefinition(BaseModel):
    """Specification of an atomic agent skill."""

    name: str
    description: str = ""
    instructions: str = ""

    model_config = ConfigDict(frozen=True)
