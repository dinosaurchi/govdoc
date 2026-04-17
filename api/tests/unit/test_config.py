"""Unit tests for app.core.config Settings class."""

import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_settings_loads_with_defaults():
    s = Settings(
        _env_file=None,
        DATABASE_URL="sqlite:///data/secureflow.db",
    )
    assert s.APP_ENV == "development"
    assert s.APP_PORT == 8000
    assert s.WEB_PORT == 3000
    assert s.API_BASE_URL == "http://localhost:8000"
    assert s.ENABLE_DEMO_MODE is False
    assert s.ENABLE_CACHED_AI_RESULTS is False
    assert s.ENABLE_LIVE_OCR is True
    assert s.ENABLE_LIVE_EMBEDDINGS is True


@pytest.mark.unit
def test_config_paths_have_correct_defaults():
    s = Settings(_env_file=None, DATABASE_URL="sqlite:///data/secureflow.db")
    assert s.MODELS_CONFIG_PATH == "api/config/models.yaml"
    assert s.ROLES_CONFIG_PATH == "api/config/roles.yaml"
    assert s.PROMPT_CONFIG_PATH == "api/prompts"


@pytest.mark.unit
def test_validate_ai_config_raises_when_api_key_empty():
    s = Settings(
        _env_file=None,
        MODELSTUDIO_API_KEY="",
        MODELSTUDIO_BASE_URL="https://example.com",
        MODELSTUDIO_DASHSCOPE_URL="https://example.com",
    )
    with pytest.raises(ValueError, match="MODELSTUDIO_API_KEY"):
        s.validate_ai_config()


@pytest.mark.unit
def test_validate_ai_config_raises_when_base_url_empty():
    s = Settings(
        _env_file=None,
        MODELSTUDIO_API_KEY="sk-test",
        MODELSTUDIO_BASE_URL="",
        MODELSTUDIO_DASHSCOPE_URL="https://example.com",
    )
    with pytest.raises(ValueError, match="MODELSTUDIO_BASE_URL"):
        s.validate_ai_config()


@pytest.mark.unit
def test_validate_ai_config_raises_when_dashscope_url_empty():
    s = Settings(
        _env_file=None,
        MODELSTUDIO_API_KEY="sk-test",
        MODELSTUDIO_BASE_URL="https://example.com",
        MODELSTUDIO_DASHSCOPE_URL="",
    )
    with pytest.raises(ValueError, match="MODELSTUDIO_DASHSCOPE_URL"):
        s.validate_ai_config()


@pytest.mark.unit
def test_validate_ai_config_passes_when_all_set():
    s = Settings(
        _env_file=None,
        MODELSTUDIO_API_KEY="sk-test",
        MODELSTUDIO_BASE_URL="https://example.com",
        MODELSTUDIO_DASHSCOPE_URL="https://example.com",
    )
    s.validate_ai_config()  # should not raise


@pytest.mark.unit
def test_validate_remote_config_raises_when_host_empty():
    s = Settings(
        _env_file=None,
        REMOTE_HOST="",
        REMOTE_USER="deploy",
        REMOTE_APP_DIR="/opt/app",
    )
    with pytest.raises(ValueError, match="REMOTE_HOST"):
        s.validate_remote_config()


@pytest.mark.unit
def test_validate_remote_config_raises_when_user_empty():
    s = Settings(
        _env_file=None,
        REMOTE_HOST="server.example.com",
        REMOTE_USER="",
        REMOTE_APP_DIR="/opt/app",
    )
    with pytest.raises(ValueError, match="REMOTE_USER"):
        s.validate_remote_config()


@pytest.mark.unit
def test_validate_remote_config_raises_when_app_dir_empty():
    s = Settings(
        _env_file=None,
        REMOTE_HOST="server.example.com",
        REMOTE_USER="deploy",
        REMOTE_APP_DIR="",
    )
    with pytest.raises(ValueError, match="REMOTE_APP_DIR"):
        s.validate_remote_config()


@pytest.mark.unit
def test_validate_remote_config_passes_when_all_set():
    s = Settings(
        _env_file=None,
        REMOTE_HOST="server.example.com",
        REMOTE_USER="deploy",
        REMOTE_APP_DIR="/opt/app",
    )
    s.validate_remote_config()  # should not raise
