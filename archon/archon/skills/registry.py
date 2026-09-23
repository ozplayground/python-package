"""Skill registry managing available skills and prompt injection formatting."""
from typing import Dict, Iterator, List, Optional
from archon.skills.definition import SkillDefinition


class SkillRegistry:
    """Catalog of atomic agent skills available within an execution session."""

    def __init__(self, skills: Optional[Dict[str, SkillDefinition]] = None) -> None:
        self._skills: Dict[str, SkillDefinition] = dict(skills or {})

    def register(self, skill: SkillDefinition) -> None:
        """Register a SkillDefinition instance."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Retrieve a skill definition by name."""
        return self._skills.get(name)

    def get_prompt_injection(self, skill_names: List[str]) -> str:
        """Format requested skills into markdown text for system prompt injection."""
        sections: List[str] = []
        for name in skill_names:
            skill = self.get(name)
            if skill:
                desc = f" ({skill.description})" if skill.description else ""
                section = f"### Skill: {skill.name}{desc}\n{skill.instructions}"
                sections.append(section)
        return "\n\n".join(sections)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __iter__(self) -> Iterator[str]:
        return iter(self._skills)

    def __len__(self) -> int:
        return len(self._skills)
