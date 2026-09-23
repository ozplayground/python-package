"""Abstract harness provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:
    from archon.harness.manifest import HarnessManifest


class HarnessProvider(ABC):
    """Abstract base provider for loading and compiling harness governance."""

    @abstractmethod
    def load(self) -> HarnessManifest:
        """Load, validate, and return the immutable HarnessManifest."""

    @staticmethod
    def from_fs(base_path: Union[str, Path]) -> "HarnessProvider":
        """Instantiate FileSystemHarnessProvider for a directory path."""
        from archon.harness.fs_provider import FileSystemHarnessProvider
        return FileSystemHarnessProvider(base_path=base_path)

    @staticmethod
    def from_upload(archive_bytes: bytes) -> "HarnessProvider":
        """Instantiate InMemoryHarnessProvider from zip archive bytes."""
        from archon.harness.memory_provider import InMemoryHarnessProvider
        return InMemoryHarnessProvider(archive_bytes=archive_bytes)

    @staticmethod
    def from_db(
        records: Optional[Dict[str, Any]] = None,
        db_session: Any = None,
        tenant_id: str = "default",
    ) -> "HarnessProvider":
        """Instantiate DatabaseHarnessProvider from database records or session."""
        from archon.harness.db_provider import DatabaseHarnessProvider
        return DatabaseHarnessProvider(
            records=records,
            db_session=db_session,
            tenant_id=tenant_id,
        )
