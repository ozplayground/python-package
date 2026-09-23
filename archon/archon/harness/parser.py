"""Parser for AGENTS.md, rules, skills, and subagent declarations."""
from typing import Any, Dict, Optional, Tuple
import yaml

from archon.exceptions import HarnessParseError
from archon.harness.manifest import HarnessManifest
from archon.skills.definition import SkillDefinition
from archon.subagents.definition import SubagentDefinition


class HarnessParser:
    """Parses raw text and frontmatter into structured harness models."""

    @staticmethod
    def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
        """Split markdown content into YAML frontmatter and body."""
        content = content.strip()
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        raw_yaml = parts[1].strip()
        body = parts[2].strip()

        try:
            frontmatter = yaml.safe_load(raw_yaml) or {}
            if not isinstance(frontmatter, dict):
                frontmatter = {}
            return frontmatter, body
        except Exception as e:
            raise HarnessParseError(f"Failed to parse YAML frontmatter: {e}") from e

    @classmethod
    def parse_files(
        cls,
        files: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HarnessManifest:
        """Parse dictionary of relative file paths to content into HarnessManifest."""
        # Find constitution
        constitution = ""
        for key in ("AGENTS.md", "agents.md"):
            if key in files:
                constitution = files[key]
                break

        if not constitution:
            raise HarnessParseError("Required constitution file 'AGENTS.md' was not found in harness.")

        rules: Dict[str, str] = {}
        skills: Dict[str, SkillDefinition] = {}
        subagents: Dict[str, SubagentDefinition] = {}

        for path, content in files.items():
            norm_path = path.replace("\\", "/").strip("/")

            # Rule files: .agents/rules/*.md
            if norm_path.startswith(".agents/rules/") and norm_path.endswith(".md"):
                filename = norm_path.split("/")[-1]
                rules[filename] = content.strip()

            # Skill files: .agents/skills/<skill_name>/SKILL.md or .agents/skills/<skill_name>.md
            elif norm_path.startswith(".agents/skills/") and (
                norm_path.endswith("/SKILL.md") or norm_path.endswith(".md")
            ):
                meta, body = cls.parse_frontmatter(content)
                skill_name = meta.get("name")
                if not skill_name:
                    # fallback to directory or filename
                    parts = norm_path.split("/")
                    skill_name = parts[-2] if norm_path.endswith("/SKILL.md") else parts[-1][:-3]

                skills[skill_name] = SkillDefinition(
                    name=skill_name,
                    description=meta.get("description", ""),
                    instructions=body,
                )

            # Subagent files: .agents/subagents/<name>.md
            elif norm_path.startswith(".agents/subagents/") and norm_path.endswith(".md"):
                meta, body = cls.parse_frontmatter(content)
                subagent_name = meta.get("name")
                if not subagent_name:
                    subagent_name = norm_path.split("/")[-1][:-3]

                subagents[subagent_name] = SubagentDefinition(
                    name=subagent_name,
                    description=meta.get("description", ""),
                    system_prompt=body or meta.get("system_prompt", ""),
                    allowed_tools=meta.get("allowed_tools", []),
                    required_skills=meta.get("required_skills", []),
                    max_turns=meta.get("max_turns", 10),
                    timeout_seconds=meta.get("timeout_seconds", 120.0),
                )

        # Enforce Rule 5 skill isolation check
        from archon.skills.loader import SkillLoader
        SkillLoader().validate_isolation(skills)

        return HarnessManifest(
            constitution=constitution,
            rules=rules,
            skills=skills,
            subagents=subagents,
            metadata=metadata or {},
        )
