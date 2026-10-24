"""Unit tests for deliberate containment and adversarial prompt injection exfiltration."""

import json
from pathlib import Path
import pytest
from app.services.containment import ContainmentTestRunner


def test_prompt_injection_containment_blocked():
    """Verify prompt-injection exfiltration is blocked and host remains untouched."""
    runner = ContainmentTestRunner()
    result = runner.run_containment_test()

    assert result["attack"] == "prompt_injection_exfil"
    assert result["blocked"] is True
    assert result["host_untouched"] is True
    assert len(result["evidence_paths"]) >= 1

    # Verify log file exists and is populated
    for ep in result["evidence_paths"]:
        p = Path(ep)
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "CONTAINMENT TEST AUDIT LOG" in content
        assert "BLOCKED" in content.upper()
