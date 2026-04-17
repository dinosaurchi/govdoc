"""Unit tests for PromptRegistry."""

import hashlib
from unittest.mock import MagicMock

import pytest

from app.services.prompt_registry import PromptRegistry


@pytest.mark.unit
class TestPromptRegistryHashComputation:
    def test_hash_computation_for_known_content(self, tmp_path):
        """Verify hash matches SHA-256[:12] of the file bytes."""
        content = "This is a test classify prompt.\n"
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_bytes(content.encode("utf-8"))

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        registry = PromptRegistry(prompts_dir, mock_db)
        registry.register_all()

        assert registry.get_prompt_version("classify") == expected_hash

    def test_registry_returns_correct_version_ids(self, tmp_path):
        """Multiple prompt files get distinct version IDs."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_text("classify prompt")
        (prompts_dir / "summarize.txt").write_text("summarize prompt")
        (prompts_dir / "route.txt").write_text("route prompt")
        (prompts_dir / "escalate.txt").write_text("escalate prompt")

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        registry = PromptRegistry(prompts_dir, mock_db)
        registry.register_all()

        assert registry.get_prompt_version("classify") is not None
        assert registry.get_prompt_version("summarize") is not None
        assert registry.get_prompt_version("route") is not None
        assert registry.get_prompt_version("escalate") is not None
        # All should be distinct
        versions = [
            registry.get_prompt_version("classify"),
            registry.get_prompt_version("summarize"),
            registry.get_prompt_version("route"),
            registry.get_prompt_version("escalate"),
        ]
        assert len(set(versions)) == 4

    def test_non_stage_files_are_skipped(self, tmp_path):
        """Files whose names don't match an AnalysisStage are skipped."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_text("classify prompt")
        (prompts_dir / "README.md").write_text("not a prompt")
        (prompts_dir / "random.txt").write_text("random stuff")

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        registry = PromptRegistry(prompts_dir, mock_db)
        registry.register_all()

        assert registry.get_prompt_version("classify") is not None
        assert registry.get_prompt_version("README") is None
        assert registry.get_prompt_version("random") is None


@pytest.mark.unit
class TestPromptRegistryGetText:
    def test_get_prompt_text_returns_content(self, tmp_path):
        """get_prompt_text reads the file and returns its string content."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        content = "Classify this: {text}"
        (prompts_dir / "classify.txt").write_text(content)

        mock_db = MagicMock()
        registry = PromptRegistry(prompts_dir, mock_db)

        assert registry.get_prompt_text("classify") == content

    def test_get_prompt_text_returns_none_for_missing(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        mock_db = MagicMock()
        registry = PromptRegistry(prompts_dir, mock_db)

        assert registry.get_prompt_text("nonexistent") is None


@pytest.mark.unit
class TestPromptRegistryRegisterAll:
    def test_register_all_with_mock_db_session(self, tmp_path):
        """register_all should add PromptVersion rows to the DB session."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_text("classify prompt")

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        registry = PromptRegistry(prompts_dir, mock_db)
        registry.register_all()

        # Verify db.add was called for the new prompt version
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the added object has correct attributes
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.id == hashlib.sha256(b"classify prompt").hexdigest()[:12]
        assert added_obj.stage.value == "classify"

    def test_register_all_upserts_existing(self, tmp_path):
        """If a prompt version already exists, it should update file_path instead of adding."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_text("classify prompt")

        existing_pv = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = existing_pv

        registry = PromptRegistry(prompts_dir, mock_db)
        registry.register_all()

        # Should NOT call db.add since it's an update
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    def test_register_all_raises_on_missing_dir(self, tmp_path):
        mock_db = MagicMock()
        registry = PromptRegistry(tmp_path / "nonexistent", mock_db)

        with pytest.raises(FileNotFoundError, match="Prompts directory not found"):
            registry.register_all()

    def test_labels_applied_to_versions(self, tmp_path):
        """Labels from config are applied to prompt versions."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "classify.txt").write_text("classify prompt")

        expected_hash = hashlib.sha256(b"classify prompt").hexdigest()[:12]
        labels = {f"classify/{expected_hash}": "v1.0 - initial classify"}

        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        registry = PromptRegistry(prompts_dir, mock_db, labels=labels)
        registry.register_all()

        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.label == "v1.0 - initial classify"
