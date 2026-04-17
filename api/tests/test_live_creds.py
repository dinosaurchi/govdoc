"""Live credential tests gated by --creds flag per §18.3."""

from __future__ import annotations

import pytest


@pytest.mark.creds
class TestLiveCredentials:
    def test_qwen_plus_available(self):
        from app.adapters.modelstudio.credentials import probe_live_credentials

        results = probe_live_credentials()
        assert results["qwen-plus (classify)"] is True

    def test_qwen_max_available(self):
        from app.adapters.modelstudio.credentials import probe_live_credentials

        results = probe_live_credentials()
        assert results["qwen-max (escalate)"] is True

    def test_embedding_available(self):
        from app.adapters.modelstudio.credentials import probe_live_credentials

        results = probe_live_credentials()
        assert results["text-embedding-v4 (embed)"] is True

    def test_ocr_available(self):
        from app.adapters.modelstudio.credentials import probe_live_credentials

        results = probe_live_credentials()
        assert results["qwen-vl-plus (ocr)"] is True

    def test_rerank_available(self):
        from app.adapters.modelstudio.credentials import probe_live_credentials

        results = probe_live_credentials()
        assert results["qwen3-rerank (rerank)"] is True
