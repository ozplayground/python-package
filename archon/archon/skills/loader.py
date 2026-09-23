"""Skill loader with Rule 5 cross-skill isolation verification."""
import os
import re
from pathlib import Path
from typing import Any, Dict, Union

from archon.exceptions import SkillIsolationError
from archon.skills.definition import SkillDefinition
import yaml


class SkillLoader:
    """Loads and lints skill markdown files with atomic isolation enforcement."""

    def validate_isolation(self, skills: Dict[str, SkillDefinition]) -> None:
        """Enforce Rule 5: Skills must remain orthogonal and never cross-reference each other."""
        from archon.skills.linter import SkillLinter

        skill_names = list(skills.keys())
        for name, skill in skills.items():
            linter = SkillLinter(current_skill_name=name)
            linter.lint(skill.instructions, skill_names)

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        content = content.strip()
        if not content.startswith("---"):
            return {}, content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        try:
            meta = yaml.safe_load(parts[1].strip()) or {}
            return meta if isinstance(meta, dict) else {}, parts[2].strip()
        except Exception:
            return {}, parts[2].strip()

    def load_directory(self, skills_dir: Union[str, Path]) -> Dict[str, SkillDefinition]:
        """Scan directory, parse all skill definitions, and run isolation linting."""
        dir_path = Path(skills_dir).resolve()
        skills: Dict[str, SkillDefinition] = {}

        if not dir_path.exists() or not dir_path.is_dir():
            return skills

        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                if filename == "SKILL.md" or filename.endswith(".md"):
                    file_path = Path(root) / filename
                    content = file_path.read_text(encoding="utf-8")
                    meta, body = self._parse_frontmatter(content)

                    skill_name = meta.get("name")
                    if not skill_name:
                        skill_name = (
                            file_path.parent.name
                            if filename == "SKILL.md"
                            else filename[:-3]
                        )

                    skills[skill_name] = SkillDefinition(
                        name=skill_name,
                        description=meta.get("description", ""),
                        instructions=body,
                    )

        # Enforce Rule 5 linter
        self.validate_isolation(skills)
        return skills
