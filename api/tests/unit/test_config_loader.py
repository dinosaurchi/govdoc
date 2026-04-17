"""Unit tests for config loaders."""

import pytest
import yaml
from pathlib import Path

from app.core.config_loader import (
    load_models_config,
    load_roles_config,
    load_prompt_versions_config,
)


@pytest.mark.unit
class TestLoadModelsConfig:
    def test_load_valid_models_config(self, tmp_path):
        config_data = {
            "models": {
                "classify": {"model": "qwen-plus", "temperature": 0.1},
                "summarize": {"model": "qwen-plus", "temperature": 0.3},
                "route": {"model": "qwen-plus", "temperature": 0.1},
                "escalate": {"model": "qwen-max", "temperature": 0.2},
                "ocr": {"model": "qwen-vl-plus", "temperature": 0.0},
                "embed": {"model": "text-embedding-v4"},
                "rerank": {"model": "qwen3-rerank"},
            }
        }
        config_file = tmp_path / "models.yaml"
        config_file.write_text(yaml.dump(config_data))

        result = load_models_config(config_file)
        assert "models" in result
        assert set(result["models"].keys()) == {"classify", "summarize", "route", "escalate", "ocr", "embed", "rerank"}

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Models config not found"):
            load_models_config(tmp_path / "nonexistent.yaml")

    def test_missing_models_key_raises_value_error(self, tmp_path):
        config_file = tmp_path / "models.yaml"
        config_file.write_text(yaml.dump({"other_key": {}}))

        with pytest.raises(ValueError, match="must contain 'models' key"):
            load_models_config(config_file)

    def test_missing_required_keys_raises_value_error(self, tmp_path):
        config_data = {"models": {"classify": {"model": "qwen-plus"}}}
        config_file = tmp_path / "models.yaml"
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(ValueError, match="missing required keys"):
            load_models_config(config_file)

    def test_loads_actual_project_config(self):
        """Test loading the real project models.yaml."""
        config_path = Path("api/config/models.yaml")
        if config_path.exists():
            result = load_models_config(config_path)
            assert "models" in result
            assert len(result["models"]) == 7


@pytest.mark.unit
class TestLoadRolesConfig:
    def test_load_valid_roles_config(self, tmp_path):
        config_data = {
            "roles": {
                "intake_clerk": {
                    "label": "Intake Clerk",
                    "allowed_actions": ["documents.create"],
                },
                "supervisor": {
                    "label": "Supervisor",
                    "allowed_actions": ["documents.close"],
                },
            }
        }
        config_file = tmp_path / "roles.yaml"
        config_file.write_text(yaml.dump(config_data))

        result = load_roles_config(config_file)
        assert "roles" in result
        assert "intake_clerk" in result["roles"]
        assert result["roles"]["intake_clerk"]["label"] == "Intake Clerk"

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Roles config not found"):
            load_roles_config(tmp_path / "nonexistent.yaml")

    def test_missing_roles_key_raises_value_error(self, tmp_path):
        config_file = tmp_path / "roles.yaml"
        config_file.write_text(yaml.dump({"other": {}}))

        with pytest.raises(ValueError, match="must contain 'roles' key"):
            load_roles_config(config_file)

    def test_loads_actual_project_config(self):
        """Test loading the real project roles.yaml."""
        config_path = Path("api/config/roles.yaml")
        if config_path.exists():
            result = load_roles_config(config_path)
            assert "roles" in result
            assert "intake_clerk" in result["roles"]


@pytest.mark.unit
class TestLoadPromptVersionsConfig:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = load_prompt_versions_config(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        config_file = tmp_path / "prompt_versions.yaml"
        config_file.write_text("")

        result = load_prompt_versions_config(config_file)
        assert result == {}

    def test_loads_valid_config(self, tmp_path):
        config_data = {"classify/abc123": "v1.0 classify prompt"}
        config_file = tmp_path / "prompt_versions.yaml"
        config_file.write_text(yaml.dump(config_data))

        result = load_prompt_versions_config(config_file)
        assert "classify/abc123" in result
