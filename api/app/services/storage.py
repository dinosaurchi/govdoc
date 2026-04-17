import hashlib
from pathlib import Path

from app.core.config import settings


class LocalFileStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.LOCAL_FILE_STORAGE_ROOT)

    def save(self, document_id: str, filename: str, content: bytes) -> dict:
        """Save file and return metadata dict."""
        doc_dir = self.root / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        storage_path = doc_dir / filename
        storage_path.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        return {
            "storage_key": str(storage_path.relative_to(self.root)),
            "size_bytes": len(content),
            "sha256": sha256,
        }

    def read(self, storage_key: str) -> bytes:
        """Read file by storage key."""
        path = self.root / storage_key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")
        return path.read_bytes()

    def exists(self, storage_key: str) -> bool:
        return (self.root / storage_key).exists()
