from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


def compute_file_checksum(file_path: Optional[PathLike]) -> Optional[str]:
    """Compute SHA-256 checksum for a file path.

    Args:
        file_path: Path to file (str or Path) or None

    Returns:
        Hex-encoded checksum string or None if file is missing or on error
    """
    if not file_path:
        return None
    try:
        path_obj = file_path if isinstance(file_path, Path) else Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return None
        h = hashlib.sha256()
        with path_obj.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        # Keep it quiet but safe — callers decide how to log/report
        return None
