"""Model Studio live credential probe per §17.7."""

from __future__ import annotations

import base64
from pathlib import Path

from app.adapters.modelstudio.client import ModelStudioClient
from app.adapters.modelstudio.rerank_client import RerankClient
from app.core.config import settings

# Load the white PNG fixture for OCR probe
_FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"
_WHITE_PNG = _FIXTURE_DIR / "white_10x10.png"


def probe_live_credentials() -> dict:
    """Run 5-model live probe per §17.7. Returns dict with locked keys."""
    results: dict = {}

    # Validate env vars first
    try:
        settings.validate_ai_config()
    except ValueError as e:
        error_msg = str(e)
        for key in [
            "qwen-plus (classify)",
            "qwen-max (escalate)",
            "text-embedding-v4 (embed)",
            "qwen-vl-plus (ocr)",
            "qwen3-rerank (rerank)",
        ]:
            results[key] = f"FAILED: {error_msg}"
        return results

    # 1. Classify (qwen-plus)
    try:
        client = ModelStudioClient()
        resp = client.chat_completion(
            "qwen-plus",
            [{"role": "user", "content": "Say 'OK' and nothing else."}],
            max_tokens=10,
        )
        results["qwen-plus (classify)"] = True if resp.strip().lower() else "FAILED: empty response"
    except Exception as e:
        results["qwen-plus (classify)"] = f"FAILED: {e}"

    # 2. Escalate (qwen-max)
    try:
        client = ModelStudioClient()
        resp = client.chat_completion(
            "qwen-max",
            [{"role": "user", "content": "Say 'OK' and nothing else."}],
            max_tokens=10,
        )
        results["qwen-max (escalate)"] = True if resp.strip().lower() else "FAILED: empty response"
    except Exception as e:
        results["qwen-max (escalate)"] = f"FAILED: {e}"

    # 3. Embed (text-embedding-v4)
    try:
        client = ModelStudioClient()
        embs = client.embeddings(["test"])
        results["text-embedding-v4 (embed)"] = (
            True if embs and len(embs[0].embedding) > 0 else "FAILED: empty embedding"
        )
    except Exception as e:
        results["text-embedding-v4 (embed)"] = f"FAILED: {e}"

    # 4. OCR (qwen-vl-plus)
    try:
        client = ModelStudioClient()
        if _WHITE_PNG.exists():
            img_b64 = base64.b64encode(_WHITE_PNG.read_bytes()).decode()
            client.ocr(img_b64)
            results["qwen-vl-plus (ocr)"] = True
        else:
            results["qwen-vl-plus (ocr)"] = "FAILED: white_10x10.png fixture not found"
    except Exception as e:
        results["qwen-vl-plus (ocr)"] = f"FAILED: {e}"

    # 5. Rerank (qwen3-rerank)
    try:
        rc = RerankClient()
        rr = rc.rerank("test query", ["test document"], top_n=1)
        results["qwen3-rerank (rerank)"] = True if rr else "FAILED: empty results"
    except Exception as e:
        results["qwen3-rerank (rerank)"] = f"FAILED: {e}"

    return results
