"""Tests for Tool engine, BashTool sandbox, security filters, and @tool decorator."""
import os
import sys
from pathlib import Path
import pytest

from archon.exceptions import ToolSecurityError
from archon.tools import (
    BaseTool,
    BashTool,
    ToolExecutionResult,
    ToolRegistry,
    tool,
)


class TestBashTool:
    """Tests for BashTool execution, timeout, directory jail, and blacklist."""

    def test_execute_safe_command_success(self, tmp_path):
        bash = BashTool(working_directory=tmp_path)
        result = bash.execute("echo 'hello archon'")

        assert result.exit_code == 0
        assert "hello archon" in result.stdout
        assert result.error is None
        assert result.duration_ms >= 0

    def test_execute_timeout_kills_process_group(self, tmp_path):
        # 0.2 second timeout running an infinite or 5 second sleep
        bash = BashTool(working_directory=tmp_path, timeout_seconds=0.2)
        cmd = f"{sys.executable} -c 'import time; time.sleep(5)'"
        result = bash.execute(cmd)

        assert result.exit_code == 124
        assert "timed out" in str(result.error).lower()

    def test_blocked_dangerous_commands_blacklist(self, tmp_path):
        bash = BashTool(working_directory=tmp_path)

        dangerous_commands = [
            "rm -rf /",
            "rm -r /home",
            "sudo apt-get install",
            "su root",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            ":(){ :|:& };:",  # fork bomb
            "shutdown -h now",
            "reboot",
            "chmod 777 /",
            "chown root /etc",
            "fdisk /dev/sdb",
            "init 0",
            "init 6",
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ToolSecurityError) as exc_info:
                bash.execute(cmd)
            assert "security" in str(exc_info.value).lower() or "blocked" in str(exc_info.value).lower()

    def test_directory_jail_prevents_escaping_working_dir(self, tmp_path):
        jail_dir = tmp_path / "jail"
        jail_dir.mkdir()
        bash = BashTool(working_directory=jail_dir)

        # Attempt to cd out of the jail
        escape_commands = [
            "cd / && ls",
            "cd /tmp && ls",
            "cd ../../ && ls",
            "cd ..",
        ]

        for cmd in escape_commands:
            with pytest.raises(ToolSecurityError) as exc_info:
                bash.execute(cmd)
            assert "jail" in str(exc_info.value).lower() or "directory" in str(exc_info.value).lower()

    def test_large_output_buffer_truncation(self, tmp_path):
        bash = BashTool(working_directory=tmp_path)
        # Generate 1.2MB of output
        cmd = f"{sys.executable} -c 'print(\"A\" * (1024 * 1024 + 100000))'"
        result = bash.execute(cmd)

        assert result.exit_code == 0
        assert result.is_truncated is True
        assert "[TRUNCATED: Output exceeded 1MB]" in result.stdout
        # Output should be clamped around 1MB + truncation notice
        assert len(result.stdout) <= (1024 * 1024 + 100)


class TestCustomToolDecorator:
    """Tests for @tool decorator and schema generation."""

    def test_tool_decorator_extracts_json_schema(self):
        @tool(name="multiply", description="Multiply two numbers")
        def multiply(x: int, y: int = 2) -> int:
            """Multiply x by y."""
            return x * y

        assert isinstance(multiply, BaseTool)
        assert multiply.name == "multiply"
        assert multiply.description == "Multiply two numbers"

        schema = multiply.parameters_schema
        assert schema["type"] == "object"
        assert "x" in schema["properties"]
        assert schema["properties"]["x"]["type"] == "integer"
        assert "y" in schema["properties"]
        assert schema["required"] == ["x"]

    def test_tool_execution(self):
        @tool(name="greet")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        res = greet.execute(name="Alice")
        assert isinstance(res, ToolExecutionResult)
        assert res.exit_code == 0
        assert res.stdout == "Hello, Alice!"


class TestToolRegistry:
    """Tests for ToolRegistry and clone operations."""

    def test_registry_and_clone(self, tmp_path):
        registry = ToolRegistry()
        bash = BashTool(working_directory=tmp_path)
        registry.register(bash)

        @tool(name="ping")
        def ping() -> str:
            return "pong"

        registry.register(ping)

        assert "bash" in registry
        assert "ping" in registry

        schemas = registry.get_schemas()
        assert len(schemas) == 2

        # Clone creates an independent copy
        cloned = registry.clone()
        assert "bash" in cloned
        assert "ping" in cloned

        # Modifying cloned does not affect original
        @tool(name="extra")
        def extra() -> str:
            return "extra"

        cloned.register(extra)
        assert "extra" in cloned
        assert "extra" not in registry
