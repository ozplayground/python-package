"""In-memory Zip archive harness provider with ZipSlip path traversal defense."""
import io
import os
import zipfile
from typing import Dict

from archon.exceptions import HarnessSecurityError
from archon.harness.manifest import HarnessManifest
from archon.harness.parser import HarnessParser
from archon.harness.provider import HarnessProvider


class InMemoryHarnessProvider(HarnessProvider):
    """Loads and compiles harness definitions directly from in-memory zip bytes."""

    def __init__(self, archive_bytes: bytes) -> None:
        self.archive_bytes = archive_bytes

    def load(self) -> HarnessManifest:
        """Extract files in-memory safely with ZipSlip protection."""
        files: Dict[str, str] = {}
        fake_base = "/archive_root"

        try:
            with zipfile.ZipFile(io.BytesIO(self.archive_bytes)) as zf:
                for member in zf.infolist():
                    filename = member.filename

                    # Normalize and detect ZipSlip path traversal
                    norm_path = os.path.normpath(filename)
                    if norm_path.startswith("..") or "/../" in filename or "\\..\\" in filename:
                        raise HarnessSecurityError(
                            f"ZipSlip path traversal attempt detected in archive: {filename}"
                        )

                    resolved_path = os.path.abspath(os.path.join(fake_base, filename))
                    if not resolved_path.startswith(fake_base + os.sep) and resolved_path != fake_base:
                        raise HarnessSecurityError(
                            f"ZipSlip path traversal attempt detected in archive: {filename}"
                        )

                    if member.is_dir():
                        continue

                    if filename.endswith(".md"):
                        try:
                            content = zf.read(member).decode("utf-8")
                            files[filename] = content
                        except UnicodeDecodeError:
                            continue
        except zipfile.BadZipFile as e:
            raise HarnessSecurityError(f"Invalid or corrupted zip archive: {e}") from e

        return HarnessParser.parse_files(files, metadata={"source": "in_memory_zip"})
