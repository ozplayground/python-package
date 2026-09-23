"""Tests for SkillLinter, SkillIsolationError zero tolerance, and line number extraction."""
import pytest

from archon.exceptions import SkillIsolationError
from archon.skills import SkillLinter


class TestSkillLinterIsolation:
    """TDD tests for SkillLinter."""

    def test_lint_clean_isolated_skill_returns_true(self):
        content = """# Clean Skill
This skill performs isolated text formatting.
Do not depend on anything else.
"""
        linter = SkillLinter()
        assert linter.lint(content, ["git", "tdd"]) is True

    def test_lint_detects_skill_name_reference_with_line_number(self):
        content = """# Orchestration Skill
Line 2
Line 3
Here we call the tdd skill to execute testing.
Line 5
"""
        linter = SkillLinter()
        with pytest.raises(SkillIsolationError) as exc_info:
            linter.lint(content, ["tdd", "git"])

        err_text = str(exc_info.value)
        assert "tdd" in err_text
        assert "line 4" in err_text.lower() or "4" in err_text

    def test_lint_detects_relative_path_include_reference(self):
        content = """# DB Skill
Check guidelines in ../cache_skill/SKILL.md before saving.
"""
        linter = SkillLinter(current_skill_name="db")
        with pytest.raises(SkillIsolationError) as exc_info:
            linter.lint(content, ["db"])

        assert "relative" in str(exc_info.value).lower() or "cache_skill" in str(exc_info.value).lower()

    def test_lint_detects_import_or_decorator_syntax(self):
        content = """# Advanced Skill
@skill(name="helper")
include skill logging
"""
        linter = SkillLinter()
        with pytest.raises(SkillIsolationError) as exc_info:
            linter.lint(content, ["helper", "logging"])

        assert "isolation" in str(exc_info.value).lower()
