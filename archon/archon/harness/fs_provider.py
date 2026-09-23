"""File system harness provider."""
import os
from pathlib import Path
from typing import Dict, Union

from archon.harness.manifest import HarnessManifest
from archon.harness.parser import HarnessParser
from archon.harness.provider import HarnessProvider


class FileSystemHarnessProvider(HarnessProvider):
    """Loads harness definition from a local directory."""

    def __init__(self, base_path: Union[str, Path]) -> None:
        self.base_path = Path(base_path).resolve()

    def load(self) -> HarnessManifest:
        """Scan directory and parse all files into a manifest."""
        files: Dict[str, str] = {}

        if not self.base_path.exists() or not self.base_path.is_dir():
            raise FileNotFoundError(f"Harness directory '{self.base_path}' does not exist.")

        for root, _, filenames in os.walk(self.base_path):
            for filename in filenames:
                if filename.endswith(".md"):
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(self.base_path).as_posix()
                    try:
                        files[rel_path] = full_path.read_text(encoding="utf-8")
                    except Exception:
                        pass

        return HarnessParser.parse_files(files, metadata={"source": "filesystem", "path": str(self.base_path)})
