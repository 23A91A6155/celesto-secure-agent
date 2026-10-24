"""Unit tests for sandbox lifecycle management, naming, and cleanup guarantees."""

import json
from pathlib import Path
import pytest

from app.schemas import SANDBOX_NAME_REGEX
from app.services.lifecycle import (
    LifecycleManager,
    generate_sandbox_name,
)


def test_sandbox_name_generator_format():
    """Verify generated sandbox names conform strictly to ^sbx-[a-z0-9]{8,}$."""
    names = [generate_sandbox_name() for _ in range(50)]
    for name in names:
        assert SANDBOX_NAME_REGEX.match(name) is not None
        assert name.startswith("sbx-")
        assert len(name) >= 12
    # Ensure collision-resistance
    assert len(names) == len(set(names))


def test_lifecycle_report_generation(tmp_path):
    """Verify reports/lifecycle.json schema and boolean True cleanup flags."""
    rep_file = tmp_path / "lifecycle.json"
    manager = LifecycleManager()
    sbx1 = generate_sandbox_name("sbx-test1")
    sbx2 = generate_sandbox_name("sbx-test2")
    manager.record_sandbox(sbx1)
    manager.record_sandbox(sbx2)

    rep = manager.write_lifecycle_report(str(rep_file))
    assert rep["cleanup_on_success"] is True
    assert rep["cleanup_on_failure"] is True
    assert rep["cleanup_on_interrupt"] is True
    assert sbx1 in rep["sandbox_names"]
    assert sbx2 in rep["sandbox_names"]

    # Verify on-disk file
    data = json.loads(rep_file.read_text(encoding="utf-8"))
    assert data["cleanup_on_success"] is True
    assert len(data["sandbox_names"]) >= 2
