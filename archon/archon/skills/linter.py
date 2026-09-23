"""Static linter enforcing Skill Isolation Principle (Rule 5)."""
from __future__ import annotations

import re
from typing import List, Optional

from archon.exceptions import SkillIsolationError


class SkillLinter:
    """Enforces atomic isolation across skill definitions."""

    def __init__(self, current_skill_name: Optional[str] = None) -> None:
        self.current_skill_name = current_skill_name

    def lint(self, skill_content: str, registered_skill_names: List[str]) -> bool:
        """Lint skill markdown text against cross-skill references and relative imports.

        Raises:
            SkillIsolationError: If any prohibited cross-reference is detected.

        Returns:
            True if isolation check passed.
        """
        lines = skill_content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            # Check relative path references (e.g. ../other_skill/SKILL.md)
            rel_match = re.search(
                r"(\.\./[a-zA-Z0-9_\-]+/SKILL\.md|\.\./skills/|\bskills/)",
                line,
                re.IGNORECASE,
            )
            if rel_match:
                skill_id = f"'{self.current_skill_name}' " if self.current_skill_name else ""
                raise SkillIsolationError(
                    f"Skill {skill_id}violates Rule 5 (Skill Isolation Principle) by referencing relative skill path at line {line_num}: '{line.strip()}'"
                )

            # Check @skill or include skill directives
            if re.search(r"(@skill\([^\)]+\)|include\s+skill)", line, re.IGNORECASE):
                skill_id = f"'{self.current_skill_name}' " if self.current_skill_name else ""
                raise SkillIsolationError(
                    f"Skill {skill_id}violates Rule 5 (Skill Isolation Principle) by using skill import syntax at line {line_num}: '{line.strip()}'"
                )

            # Check explicit mentions of other skill names
            for other_name in registered_skill_names:
                if self.current_skill_name and other_name == self.current_skill_name:
                    continue
                # Full word boundary match
                pattern = rf"\b{re.escape(other_name)}\b"
                if re.search(pattern, line, re.IGNORECASE):
                    skill_id = f"'{self.current_skill_name}' " if self.current_skill_name else ""
                    raise SkillIsolationError(
                        f"Skill {skill_id}violates Rule 5 (Skill Isolation Principle) by referencing another skill '{other_name}' at line {line_num}: '{line.strip()}'"
                    )

        return True
