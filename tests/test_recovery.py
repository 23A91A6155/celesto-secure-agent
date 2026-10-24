"""Unit tests for Step 7 Failure Injection and Rollback Recovery Workflow."""

import json
from pathlib import Path
import pytest
from app.services.recovery import RecoveryWorkflow


def test_recovery_workflow_execution(tmp_path):
    """Verify 10-step sequence, step 7 failure injection, and rollback policy trace."""
    trace_file = tmp_path / "failure_trace.jsonl"
    policy_file = tmp_path / "failure_policy.json"

    workflow = RecoveryWorkflow(policy="rollback")
    result = workflow.execute_workflow(
        trace_path=str(trace_file),
        policy_path=str(policy_file),
    )

    assert result["failed_step"] == 7
    assert result["total_steps"] == 10
    assert result["policy"] == "rollback"

    # Verify policy file content
    policy_data = json.loads(policy_file.read_text(encoding="utf-8"))
    assert policy_data["failed_step"] == 7
    assert policy_data["total_steps"] == 10
    assert policy_data["policy"] == "rollback"
    assert len(policy_data["rationale"]) >= 200

    # Verify trace entries
    lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 10

    # Ensure policy_applied event exists with exact policy
    applied_events = [e for e in lines if e.get("event") == "policy_applied"]
    assert len(applied_events) == 1
    assert applied_events[0]["policy"] == "rollback"
    assert applied_events[0]["step"] == 7
