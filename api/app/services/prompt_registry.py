"""PromptRegistry — scans prompt files, computes hashes, and upserts into DB."""

import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.system import PromptVersion
from app.models.document import AnalysisStage


class PromptRegistry:
    def __init__(self, prompts_dir: str | Path, db: Session, labels: dict | None = None):
        self.prompts_dir = Path(prompts_dir)
        self.db = db
        self.labels = labels or {}
        self._cache: dict[str, str] = {}  # stage -> prompt_version id (hash)

    def register_all(self):
        """Scan prompts dir, compute hashes, upsert into DB."""
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        for prompt_file in sorted(self.prompts_dir.glob("*.txt")):
            stage_name = prompt_file.stem  # e.g. "classify"
            try:
                stage = AnalysisStage(stage_name)
            except ValueError:
                continue  # skip files that don't match a stage

            file_bytes = prompt_file.read_bytes()
            hash_id = hashlib.sha256(file_bytes).hexdigest()[:12]

            # Upsert
            existing = self.db.query(PromptVersion).filter_by(id=hash_id, stage=stage).first()
            if existing:
                existing.file_path = str(prompt_file)
                existing.label = self.labels.get(f"{stage_name}/{hash_id}")
            else:
                pv = PromptVersion(
                    id=hash_id,
                    stage=stage,
                    file_path=str(prompt_file),
                    label=self.labels.get(f"{stage_name}/{hash_id}"),
                )
                self.db.add(pv)

            self._cache[stage_name] = hash_id

        self.db.commit()

    def get_prompt_version(self, stage: str) -> str | None:
        """Get the current prompt version hash for a stage."""
        return self._cache.get(stage)

    def get_prompt_text(self, stage: str) -> str | None:
        """Load the prompt text for a given stage."""
        prompt_file = self.prompts_dir / f"{stage}.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return None

    def get_all_versions(self) -> list[dict]:
        """Return all registered prompt versions."""
        pvs = self.db.query(PromptVersion).all()
        return [{"id": pv.id, "stage": pv.stage.value, "file_path": pv.file_path, "label": pv.label} for pv in pvs]
