"""Tests for HarnessProvider factories, ZipSlip defense variations, and parser error paths."""
import io
import zipfile
from pathlib import Path
import pytest

from archon.exceptions import (
    HarnessParseError,
    HarnessSecurityError,
)
from archon.harness import (
    DatabaseHarnessProvider,
    FileSystemHarnessProvider,
    HarnessManifest,
    HarnessParser,
    HarnessProvider,
    InMemoryHarnessProvider,
)


class TestHarnessProviderFactoriesAndEdges:
    """TDD tests for HarnessProvider static factories and edge cases."""

    def test_factory_from_fs(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Constitution from Factory")
        provider = HarnessProvider.from_fs(tmp_path)
        assert isinstance(provider, FileSystemHarnessProvider)
        manifest = provider.load()
        assert "Constitution from Factory" in manifest.constitution

    def test_factory_from_upload(self):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AGENTS.md", "# Uploaded Constitution")
        provider = HarnessProvider.from_upload(zip_buf.getvalue())
        assert isinstance(provider, InMemoryHarnessProvider)
        manifest = provider.load()
        assert "Uploaded Constitution" in manifest.constitution

    def test_factory_from_db(self):
        records = {
            "constitution": "# DB Constitution",
            "rules": {"auth.md": "Enforce RBAC"},
        }
        provider = HarnessProvider.from_db(records=records, tenant_id="acme_corp")
        assert isinstance(provider, DatabaseHarnessProvider)
        manifest = provider.load()
        assert manifest.metadata["tenant_id"] == "acme_corp"
        assert "DB Constitution" in manifest.constitution

    @pytest.mark.parametrize(
        "malicious_path",
        [
            "../secret.txt",
            "../../etc/shadow",
            "sub/../../escape.md",
            "..\\..\\windows_escape.txt",
            "/absolute/root/escape.md",
        ],
    )
    def test_zipslip_traversal_payload_variations_blocked(self, malicious_path):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AGENTS.md", "# Safe")
            zf.writestr(malicious_path, "evil payload")

        provider = InMemoryHarnessProvider(zip_buf.getvalue())
        with pytest.raises(HarnessSecurityError):
            provider.load()

    def test_malformed_yaml_frontmatter_raises_parse_error(self):
        malformed_markdown = """---
name: broken_skill
description: [unclosed list
---
Instructions here.
"""
        with pytest.raises(HarnessParseError) as exc_info:
            HarnessParser.parse_frontmatter(malformed_markdown)
        assert "YAML" in str(exc_info.value) or "frontmatter" in str(exc_info.value).lower()
