"""Database harness provider for multi-tenant deployments."""
from typing import Any, Dict, Optional

from archon.harness.manifest import HarnessManifest
from archon.harness.provider import HarnessProvider
from archon.skills.definition import SkillDefinition
from archon.subagents.definition import SubagentDefinition


class DatabaseHarnessProvider(HarnessProvider):
    """Loads harness definition from database records or tenant dictionary."""

    def __init__(
        self,
        records: Optional[Dict[str, Any]] = None,
        db_session: Any = None,
        tenant_id: str = "default",
    ) -> None:
        self.records = records or {}
        self.db_session = db_session
        self.tenant_id = tenant_id

    def load(self) -> HarnessManifest:
        """Construct HarnessManifest from database records."""
        constitution = self.records.get("constitution", "")
        rules = dict(self.records.get("rules", {}))

        skills: Dict[str, SkillDefinition] = {}
        raw_skills = self.records.get("skills", [])
        if isinstance(raw_skills, list):
            for s in raw_skills:
                if isinstance(s, dict) and "name" in s:
                    skills[s["name"]] = SkillDefinition(**s)
                elif isinstance(s, SkillDefinition):
                    skills[s.name] = s
        elif isinstance(raw_skills, dict):
            for k, v in raw_skills.items():
                if isinstance(v, dict):
                    skills[k] = SkillDefinition(**v)
                elif isinstance(v, SkillDefinition):
                    skills[k] = v

        subagents: Dict[str, SubagentDefinition] = {}
        raw_subagents = self.records.get("subagents", [])
        if isinstance(raw_subagents, list):
            for sa in raw_subagents:
                if isinstance(sa, dict) and "name" in sa:
                    subagents[sa["name"]] = SubagentDefinition(**sa)
                elif isinstance(sa, SubagentDefinition):
                    subagents[sa.name] = sa
        elif isinstance(raw_subagents, dict):
            for k, v in raw_subagents.items():
                if isinstance(v, dict):
                    subagents[k] = SubagentDefinition(**v)
                elif isinstance(v, SubagentDefinition):
                    subagents[k] = v

        metadata = dict(self.records.get("metadata", {}))
        metadata["tenant_id"] = self.tenant_id

        return HarnessManifest(
            constitution=constitution,
            rules=rules,
            skills=skills,
            subagents=subagents,
            metadata=metadata,
        )
