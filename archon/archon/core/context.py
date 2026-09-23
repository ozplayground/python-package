"""Execution context for agent turns and hierarchical subagent tracking."""
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ExecutionContext(BaseModel):
    """Immutable snapshot of the current execution frame and lineage."""

    session_id: str
    agent_name: str = "main"
    depth: int = 0
    caller_lineage: Tuple[str, ...] = ("main",)
    variables: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)

    def create_child(self, subagent_name: str, **extra_vars: Any) -> "ExecutionContext":
        """Create a child execution context incrementing depth and appending to lineage."""
        merged_vars = dict(self.variables)
        merged_vars.update(extra_vars)

        return ExecutionContext(
            session_id=self.session_id,
            agent_name=subagent_name,
            depth=self.depth + 1,
            caller_lineage=self.caller_lineage + (subagent_name,),
            variables=merged_vars,
        )
