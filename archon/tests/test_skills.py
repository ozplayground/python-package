"""Tests for Skill governance, loader, registry, and Rule 5 cross-skill isolation."""
from pathlib import Path
import pytest

from archon.exceptions import SkillIsolationError
from archon.skills import SkillDefinition, SkillLoader, SkillRegistry


class TestSkillRegistry:
    """Tests for SkillRegistry catalog and prompt injection."""

    def test_register_and_get_skill(self):
        registry = SkillRegistry()
        skill = SkillDefinition(
            name="python_typing",
            description="Type hinting guidelines",
            instructions="Always use Python 3.11 type annotations.",
        )
        registry.register(skill)

        retrieved = registry.get("python_typing")
        assert retrieved is not None
        assert retrieved.name == "python_typing"

    def test_get_prompt_injection(self):
        registry = SkillRegistry()
        s1 = SkillDefinition(
            name="git_hygiene",
            instructions="Keep commit messages concise.",
        )
        s2 = SkillDefinition(
            name="clean_code",
            instructions="Follow SOLID principles.",
        )
        registry.register(s1)
        registry.register(s2)

        prompt_text = registry.get_prompt_injection(["git_hygiene", "clean_code"])
        assert "git_hygiene" in prompt_text
        assert "clean_code" in prompt_text
        assert "Keep commit messages concise." in prompt_text
        assert "Follow SOLID principles." in prompt_text


class TestSkillLoaderAndRule5Isolation:
    """Tests for SkillLoader and Rule 5 static linter preventing cross-skill references."""

    def test_load_valid_isolated_skills_success(self, tmp_path):
        skills_dir = tmp_path / "skills"
        s1_dir = skills_dir / "docker"
        s1_dir.mkdir(parents=True)
        (s1_dir / "SKILL.md").write_text(
            "---\nname: docker\ndescription: Docker containers\n---\nWrite multi-stage Dockerfiles."
        )

        s2_dir = skills_dir / "kubernetes"
        s2_dir.mkdir(parents=True)
        (s2_dir / "SKILL.md").write_text(
            "---\nname: kubernetes\ndescription: K8s manifests\n---\nUse Helm charts for packaging."
        )

        loader = SkillLoader()
        skills = loader.load_directory(skills_dir)

        assert len(skills) == 2
        assert "docker" in skills
        assert "kubernetes" in skills

    def test_cross_skill_name_reference_raises_skill_isolation_error(self, tmp_path):
        skills_dir = tmp_path / "skills"
        s1_dir = skills_dir / "auth"
        s1_dir.mkdir(parents=True)
        (s1_dir / "SKILL.md").write_text(
            "---\nname: auth\ndescription: Auth\n---\nHandle JWT tokens."
        )

        s2_dir = skills_dir / "payment"
        s2_dir.mkdir(parents=True)
        # Violates Rule 5 by explicitly referencing 'auth' skill
        (s2_dir / "SKILL.md").write_text(
            "---\nname: payment\ndescription: Payment\n---\nFirst execute the auth skill before charging."
        )

        loader = SkillLoader()
        with pytest.raises(SkillIsolationError) as exc_info:
            loader.load_directory(skills_dir)

        err_msg = str(exc_info.value).lower()
        assert "violates rule 5" in err_msg or "isolation" in err_msg or "referencing" in err_msg
        assert "payment" in str(exc_info.value)
        assert "auth" in str(exc_info.value)

    def test_cross_skill_relative_path_reference_raises_isolation_error(self, tmp_path):
        skills_dir = tmp_path / "skills"
        s1_dir = skills_dir / "database"
        s1_dir.mkdir(parents=True)
        (s1_dir / "SKILL.md").write_text(
            "---\nname: database\ndescription: DB\n---\nRefer to ../caching/SKILL.md for cache config."
        )

        loader = SkillLoader()
        with pytest.raises(SkillIsolationError) as exc_info:
            loader.load_directory(skills_dir)

        assert "isolation" in str(exc_info.value).lower() or "reference" in str(exc_info.value).lower()
