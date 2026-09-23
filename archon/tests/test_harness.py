"""Tests for Harness providers, parser, manifest, and ZipSlip security."""
import io
import os
import zipfile
from pathlib import Path
import pytest

from archon.exceptions import HarnessParseError, HarnessSecurityError
from archon.harness import (
    DatabaseHarnessProvider,
    FileSystemHarnessProvider,
    HarnessManifest,
    HarnessParser,
    InMemoryHarnessProvider,
)


class TestHarnessParser:
    """Tests for HarnessParser and markdown/frontmatter extraction."""

    def test_parse_agents_constitution_and_rules(self, tmp_path):
        agents_md = tmp_path / "AGENTS.md"
        agents_md.write_text("# Project Constitution\nAlways write tests first.")

        rules_dir = tmp_path / ".agents" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "01_python.md").write_text("Use Python 3.11 type hints.")

        manifest = FileSystemHarnessProvider(tmp_path).load()

        assert "Project Constitution" in manifest.constitution
        assert "01_python.md" in manifest.rules
        assert "Python 3.11" in manifest.rules["01_python.md"]


class TestFileSystemHarnessProvider:
    """Tests for FileSystemHarnessProvider."""

    def test_load_full_directory_structure(self, tmp_path):
        # Create standard harness layout
        (tmp_path / "AGENTS.md").write_text("# Root Constitution")

        rules_dir = tmp_path / ".agents" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "code_style.md").write_text("Follow PEP 8")

        skills_dir = tmp_path / ".agents" / "skills" / "tdd"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: tdd\ndescription: Test Driven Development\n---\nWrite failing tests first."
        )

        subagents_dir = tmp_path / ".agents" / "subagents"
        subagents_dir.mkdir(parents=True)
        (subagents_dir / "backend.md").write_text(
            "---\nname: backend\ndescription: Backend Engineer\nallowed_tools: [bash]\nrequired_skills: [tdd]\n---\nImplement backend APIs."
        )

        provider = FileSystemHarnessProvider(tmp_path)
        manifest = provider.load()

        assert isinstance(manifest, HarnessManifest)
        assert "Root Constitution" in manifest.constitution
        assert "code_style.md" in manifest.rules
        assert "tdd" in manifest.skills
        assert manifest.skills["tdd"].name == "tdd"
        assert "backend" in manifest.subagents
        assert manifest.subagents["backend"].name == "backend"
        assert "bash" in manifest.subagents["backend"].allowed_tools

    def test_missing_agents_md_raises_error(self, tmp_path):
        provider = FileSystemHarnessProvider(tmp_path)
        with pytest.raises(HarnessParseError) as exc_info:
            provider.load()
        assert "AGENTS.md" in str(exc_info.value)


class TestInMemoryHarnessProvider:
    """Tests for InMemoryHarnessProvider and ZipSlip path traversal defense."""

    def test_load_valid_zip_archive(self):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AGENTS.md", "# In-Memory Constitution")
            zf.writestr(".agents/rules/rule1.md", "Strict rule")
            zf.writestr(
                ".agents/skills/git/SKILL.md",
                "---\nname: git\ndescription: Git skill\n---\nAlways check git status.",
            )

        provider = InMemoryHarnessProvider(zip_buffer.getvalue())
        manifest = provider.load()

        assert "In-Memory Constitution" in manifest.constitution
        assert "rule1.md" in manifest.rules
        assert "git" in manifest.skills

    def test_zipslip_traversal_attack_is_blocked(self):
        """Verify malicious zip containing relative path traversal is intercepted."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AGENTS.md", "# Safe")
            # Malicious path attempting to break out of destination root
            zf.writestr("../../../etc/passwd", "root:x:0:0:")

        provider = InMemoryHarnessProvider(zip_buffer.getvalue())
        with pytest.raises(HarnessSecurityError) as exc_info:
            provider.load()
        assert "ZipSlip" in str(exc_info.value) or "traversal" in str(exc_info.value).lower()


class TestDatabaseHarnessProvider:
    """Tests for DatabaseHarnessProvider."""

    def test_load_from_database_dictionary_records(self):
        records = {
            "constitution": "# Database Constitution",
            "rules": {"security.md": "Never leak credentials"},
            "skills": [
                {
                    "name": "sql",
                    "description": "SQL query skill",
                    "instructions": "Use parametrized queries",
                }
            ],
            "subagents": [
                {
                    "name": "dba",
                    "description": "DB Administrator",
                    "system_prompt": "Optimize queries",
                    "allowed_tools": ["bash"],
                    "required_skills": ["sql"],
                }
            ],
        }

        provider = DatabaseHarnessProvider(records=records, tenant_id="tenant-123")
        manifest = provider.load()

        assert "Database Constitution" in manifest.constitution
        assert "security.md" in manifest.rules
        assert "sql" in manifest.skills
        assert "dba" in manifest.subagents
        assert manifest.metadata["tenant_id"] == "tenant-123"
