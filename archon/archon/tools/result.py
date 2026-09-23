"""Tool execution result model."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ToolExecutionResult(BaseModel):
    """Encapsulates the standard output, error, and status of a tool execution."""

    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    is_truncated: bool = False
    duration_ms: float = 0.0

    model_config = ConfigDict(frozen=True)

    @property
    def is_success(self) -> bool:
        """True if the tool exited with code 0 and no error."""
        return self.exit_code == 0 and self.error is None
