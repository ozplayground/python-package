"""Sandboxed BashTool with directory jail, dangerous command blacklist, and timeout."""
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, List, Pattern, Union
from pydantic import Field

from archon.exceptions import ToolSecurityError
from archon.tools.base import BaseTool
from archon.tools.result import ToolExecutionResult

MAX_OUTPUT_BUFFER = 1024 * 1024  # 1MB buffer safety threshold

DEFAULT_BLACKLIST: List[str] = [
    r"\brm\s+-[rfRF]*\s+[/~]",
    r"\b(sudo|su)\b",
    r"\bchown\b",
    r"\bchmod\s+[0-7]{3,4}\s+[/~]",
    r"\b(mkfs|dd|fdisk)\b",
    r"\b(shutdown|reboot)\b",
    r"\binit\s+[06]\b",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # Fork bomb
]


class BashTool(BaseTool):
    """Executes sandboxed bash shell commands."""

    name: str = "bash"
    description: str = "Execute a bash command in a sandboxed directory."
    parameters_schema: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                }
            },
            "required": ["command"],
        }
    )
    working_directory: Path = Field(default_factory=Path.cwd)
    timeout_seconds: float = 30.0
    blacklist_patterns: List[Pattern[str]] = Field(
        default_factory=lambda: [re.compile(p, re.IGNORECASE) for p in DEFAULT_BLACKLIST]
    )

    def __init__(
        self,
        working_directory: Union[str, Path] = ".",
        timeout_seconds: float = 30.0,
        **kwargs: Any,
    ) -> None:
        resolved_dir = Path(working_directory).resolve()
        super().__init__(
            working_directory=resolved_dir,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )

    def _validate_command(self, command: str) -> None:
        """Validate command against dangerous patterns and directory jailbreak."""
        # 1. Check blacklist
        for pattern in self.blacklist_patterns:
            if pattern.search(command):
                raise ToolSecurityError(
                    f"Command blocked by security policy (dangerous pattern detected): '{command}'"
                )

        # 2. Check directory jailbreak (cd outside working directory)
        resolved_root = str(self.working_directory.resolve())
        # Split on command separators (;, &&, ||, &, \n)
        segments = re.split(r"[;&|\n]+", command)
        for segment in segments:
            seg = segment.strip()
            if seg == "cd" or seg.startswith("cd ") or seg.startswith("cd\t"):
                target = seg[2:].strip().split()[0] if seg[2:].strip() else ""
                if not target:
                    raise ToolSecurityError("Directory jailbreak attempt: cd without target")

                if target == "/" or target.startswith("/"):
                    raise ToolSecurityError(
                        f"Directory jailbreak attempt (absolute path): '{command}'"
                    )

                # Check relative path resolution
                candidate = (self.working_directory / target).resolve()
                if candidate != self.working_directory and not str(candidate).startswith(
                    resolved_root + os.sep
                ):
                    raise ToolSecurityError(
                        f"Directory jailbreak attempt (escaping working directory): '{command}'"
                    )

    def execute(self, command: str, **kwargs: Any) -> ToolExecutionResult:
        """Run bash command with process group isolation and buffer limits."""
        self._validate_command(command)

        start_time = time.perf_counter()
        is_truncated = False
        exit_code = 0
        stdout_str = ""
        stderr_str = ""
        error_msg = None

        proc = None
        try:
            # os.setsid creates a new process group so timeouts can kill all child processes
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=str(self.working_directory),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
                text=True,
            )

            stdout_str, stderr_str = proc.communicate(timeout=self.timeout_seconds)
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            if proc is not None:
                try:
                    # Kill entire process group
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.communicate()
                except Exception:
                    pass
            exit_code = 124
            error_msg = f"Execution timed out after {self.timeout_seconds}s"

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Enforce 1MB buffer ceiling
        if len(stdout_str) > MAX_OUTPUT_BUFFER:
            stdout_str = (
                stdout_str[:MAX_OUTPUT_BUFFER] + "\n[TRUNCATED: Output exceeded 1MB]"
            )
            is_truncated = True

        if len(stderr_str) > MAX_OUTPUT_BUFFER:
            stderr_str = (
                stderr_str[:MAX_OUTPUT_BUFFER] + "\n[TRUNCATED: Output exceeded 1MB]"
            )
            is_truncated = True

        return ToolExecutionResult(
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            error=error_msg,
            is_truncated=is_truncated,
            duration_ms=round(duration_ms, 2),
        )
