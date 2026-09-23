"""Standard exception hierarchy for the archon framework."""
from typing import Any, Optional


class ArchonError(Exception):
    """Base exception for all archon errors."""

    def __init__(self, message: str = "An error occurred in archon") -> None:
        super().__init__(message)
        self.message = message


class HarnessError(ArchonError):
    """Base error for harness loading and parsing."""


class HarnessParseError(HarnessError):
    """Raised when parsing AGENTS.md or harness structure fails."""


class HarnessSecurityError(HarnessError):
    """Raised when ZipSlip or path traversal attack is detected in harness."""


class SkillError(ArchonError):
    """Base error for skill governance."""


class SkillIsolationError(SkillError):
    """Raised when a skill violates Rule 5 by referencing another skill."""


class SubagentError(ArchonError):
    """Base error for subagent operations."""


class SubagentDepthExceededError(SubagentError):
    """Raised when subagent recursion depth exceeds the configured limit (max 3)."""


class SubagentCycleDetectedError(SubagentError):
    """Raised when a circular call lineage is detected in subagent dispatch."""


class SubagentNotFoundError(SubagentError):
    """Raised when a requested subagent is not defined in the harness manifest."""


class SubagentTimeoutError(SubagentError):
    """Raised when a subagent execution exceeds its timeout."""


class ToolError(ArchonError):
    """Base error for tool execution."""


class ToolSecurityError(ToolError):
    """Raised when tool execution violates security constraints (jail, blacklist)."""


class ToolExecutionError(ToolError):
    """Raised when tool execution fails unexpectedly."""


class SessionError(ArchonError):
    """Base error for agent session operations."""


class SessionClosedError(SessionError):
    """Raised when operations are attempted on an already closed session."""


class SessionTimeoutError(SessionError):
    """Raised when an agent session exceeds its configured maximum lifetime."""


class MessageBusError(SessionError):
    """Base error for message bus operations."""


class InvalidRecipientError(MessageBusError):
    """Raised when a recipient agent is not found or registered."""


class MessageBusClosedError(MessageBusError):
    """Raised when an operation is attempted on a closed message bus."""


class HarnessNotFoundError(HarnessError):
    """Raised when a requested harness path or database tenant record is not found."""


class SkillNotFoundError(SkillError):
    """Raised when a referenced skill is not registered."""


class SubagentExecutionError(SubagentError):
    """Raised when subagent execution encounters an unhandled runtime error."""


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry."""


class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds timeout limit."""


class CommandTimeoutError(ToolTimeoutError):
    """Raised when a shell command execution exceeds timeout limit."""


class PathTraversalError(ToolSecurityError):
    """Raised when path traversal or jail escape is detected."""


class DangerousCommandError(ToolSecurityError):
    """Raised when a command matches dangerous blacklist pattern."""


class ModelError(ArchonError):
    """Base error for model adapter operations."""


class UnsupportedModelProviderError(ModelError):
    """Raised when an unsupported model provider is requested."""


class ModelAuthenticationError(ModelError):
    """Raised when model provider credentials or API key fail."""


class ModelMaxRetriesExceededError(ModelError):
    """Raised when rate limits or transient errors exceed maximum retry attempts."""


class ToolCallChunkStreamError(ModelError):
    """Raised when model streaming chunk connection is severed or corrupted."""


class ModelResponseValidationError(ModelError):
    """Raised when model response fails Pydantic schema validation."""

    def __init__(
        self,
        message: str = "Model response failed schema validation",
        raw_response: str = "",
        validation_errors: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.validation_errors = validation_errors
