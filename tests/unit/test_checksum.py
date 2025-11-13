from pathlib import Path
from unittest.mock import patch

from src.utils.checksum import compute_file_checksum


def test_checksum_none_path_returns_none():
    assert compute_file_checksum(None) is None


def test_checksum_missing_file_returns_none(tmp_path: Path):
    missing = tmp_path / "nope.txt"
    assert compute_file_checksum(missing) is None


def test_checksum_exception_during_read_returns_none(tmp_path: Path):
    p = tmp_path / "data.bin"
    p.write_bytes(b"abc")

    # Force Path.open to raise for our path in this call-site
    original_open = Path.open

    def boom(self, *args, **kwargs):  # noqa: ANN001
        if self == p:
            raise OSError("read error")
        return original_open(self, *args, **kwargs)

    with patch.object(Path, "open", new=boom):
        assert compute_file_checksum(p) is None


from pathlib import Path

from src.utils.checksum import compute_file_checksum


def test_compute_file_checksum_none():
    assert compute_file_checksum(None) is None


def test_compute_file_checksum_missing(tmp_path: Path):
    missing = tmp_path / "nope.txt"
    assert compute_file_checksum(missing) is None


def test_compute_file_checksum_happy(tmp_path: Path):
    p = tmp_path / "data.bin"
    content = b"hello world\n" * 3
    p.write_bytes(content)

    # Precomputed sha256 for content
    import hashlib

    expected = hashlib.sha256(content).hexdigest()
    assert compute_file_checksum(p) == expected
