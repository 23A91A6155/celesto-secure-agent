"""Unit tests for report generation, schema validation, and character constraints."""

import json
from pathlib import Path
import pytest

from app.services.report_generator import (
    generate_problem_report,
    generate_capabilities_report,
    generate_concurrency_report,
    generate_postmortem_report,
)


def test_problem_report_schema(tmp_path):
    """Verify reports/problem.json schema and character count thresholds."""
    out_file = tmp_path / "problem.json"
    rep = generate_problem_report(str(out_file))

    assert len(rep["who"]) >= 40
    assert len(rep["agent_work"]) >= 40
    assert len(rep["proof_output"]) >= 20
    assert rep["idea_source"] == "idea_bank"


def test_capabilities_report_schema(tmp_path):
    """Verify capabilities report schema and explanation lengths."""
    out_file = tmp_path / "capabilities.json"
    rep = generate_capabilities_report(str(out_file))

    caps = rep["capabilities"]
    assert len(caps) >= 2
    for c in caps:
        assert len(c["why"]) >= 80
        assert "evidence_path" in c


def test_concurrency_report_schema(tmp_path):
    """Verify concurrency report has >= 5 jobs and sufficient breakage notes."""
    out_file = tmp_path / "concurrency.json"
    rep = generate_concurrency_report(5, str(out_file))

    assert len(rep["jobs"]) >= 5
    for j in rep["jobs"]:
        assert j["sandbox_name"].startswith("sbx-")
        assert "started_at" in j
    assert len(rep["breakage_notes"]) >= 40


def test_postmortem_report_length(tmp_path):
    """Verify postmortem markdown content is at least 200 characters."""
    out_file = tmp_path / "postmortem.md"
    content = generate_postmortem_report(str(out_file))
    assert len(content) >= 200
    assert "# Celesto Secure AI Agent" in content
