#!/usr/bin/env python3
"""
AI Quality Evaluation Script — evaluates classification accuracy and routing quality.

Usage:
    cd api && python -m pytest tests -q -m "live or live_integration" --live --integration --tb=short
  OR standalone:
    cd /path/to/govdoc && python scripts/eval_ai_quality.py

Outputs JSON report to data/ai_quality_report.json (not committed to repo).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.core.config import settings


def main() -> None:
    report: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "skipped",
        "message": "",
        "metrics": {},
    }

    # Check if AI credentials are configured
    try:
        settings.validate_ai_config()
    except ValueError as e:
        report["status"] = "no_credentials"
        report["message"] = str(e)
        _write_report(report)
        print(f"eval_ai_quality: skipped — {e}")
        return

    # Try importing the real provider
    try:
        from app.services.ai.real_provider import RealAIProvider

        provider = RealAIProvider()
    except Exception as e:
        report["status"] = "provider_error"
        report["message"] = str(e)
        _write_report(report)
        print(f"eval_ai_quality: provider error — {e}")
        return

    # Load labeled data (if any)
    labels_dir = ROOT / "data" / "labels"
    if not labels_dir.exists():
        report["status"] = "no_labels"
        report["message"] = f"No labels directory at {labels_dir}"
        _write_report(report)
        print(f"eval_ai_quality: no labels found at {labels_dir}")
        return

    label_files = sorted(labels_dir.glob("*.json"))
    if not label_files:
        report["status"] = "no_labels"
        report["message"] = "No .json label files found"
        _write_report(report)
        print("eval_ai_quality: no .json label files found")
        return

    # Run evaluation
    results = []
    correct_classifications = 0
    total = 0

    for label_file in label_files:
        try:
            with open(label_file) as f:
                label = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            results.append({"file": label_file.name, "error": str(e)})
            continue

        text = label.get("text", "")
        expected_type = label.get("expected_type", "")

        if not text or not expected_type:
            results.append(
                {
                    "file": label_file.name,
                    "error": "Missing text or expected_type in label",
                }
            )
            continue

        try:
            classification = provider.classify(text)
            total += 1
            is_correct = classification.doc_type == expected_type
            if is_correct:
                correct_classifications += 1

            results.append(
                {
                    "file": label_file.name,
                    "expected": expected_type,
                    "predicted": classification.doc_type,
                    "confidence": classification.confidence,
                    "correct": is_correct,
                }
            )
        except Exception as e:
            results.append({"file": label_file.name, "error": str(e)})

    accuracy = correct_classifications / total if total > 0 else 0.0
    report["status"] = "completed"
    report["metrics"] = {
        "total_documents": total,
        "correct_classifications": correct_classifications,
        "accuracy": round(accuracy, 4),
    }
    report["results"] = results

    _write_report(report)
    print(
        f"eval_ai_quality: accuracy={accuracy:.2%} ({correct_classifications}/{total})"
    )


def _write_report(report: dict) -> None:
    output_path = ROOT / "data" / "ai_quality_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"eval_ai_quality: report written to {output_path}")


if __name__ == "__main__":
    main()
