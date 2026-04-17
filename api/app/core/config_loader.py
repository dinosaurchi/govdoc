"""Config loaders for YAML configuration files."""

import yaml
from pathlib import Path


def load_models_config(path: str | Path) -> dict:
    """Load and validate models.yaml. Returns dict with 'models' key containing all 7 entries."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Models config not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "models" not in data:
        raise ValueError("models.yaml must contain 'models' key")
    required_keys = {"classify", "summarize", "route", "escalate", "ocr", "embed", "rerank"}
    missing = required_keys - set(data["models"].keys())
    if missing:
        raise ValueError(f"models.yaml missing required keys: {missing}")
    return data


def load_roles_config(path: str | Path) -> dict:
    """Load and validate roles.yaml. Returns dict with 'roles' key."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Roles config not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "roles" not in data:
        raise ValueError("roles.yaml must contain 'roles' key")
    return data


def load_prompt_versions_config(path: str | Path) -> dict:
    """Load prompt_versions.yaml (optional, informational labels)."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}
