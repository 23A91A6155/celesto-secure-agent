"""Unit tests for exact reliability statistical calculations and tolerances."""

import math
import pytest
from app.services.reliability import (
    compute_median,
    compute_p90,
    compute_reliability_summary,
)
from app.services.lifecycle import generate_sandbox_name


def test_compute_median_odd():
    """Verify median calculation on odd number of observations."""
    obs = [3.0, 1.0, 2.0]
    assert compute_median(obs) == 2.0


def test_compute_median_even():
    """Verify median calculation on even number of observations (average of two central values)."""
    obs = [4.0, 1.0, 3.0, 2.0]
    # Sorted: [1.0, 2.0, 3.0, 4.0] -> (2.0 + 3.0) / 2 = 2.5
    assert compute_median(obs) == 2.5


def test_compute_p90_exact_rank():
    """Verify p90 calculation at 1-based rank ceil(0.90 * n)."""
    # For n = 10, ceil(0.90 * 10) = rank 9 -> sorted element index 8
    obs_10 = [float(i) for i in range(1, 11)]
    assert compute_p90(obs_10) == 9.0

    # For n = 20, ceil(0.90 * 20) = rank 18 -> sorted element index 17
    obs_20 = [float(i) for i in range(1, 21)]
    assert compute_p90(obs_20) == 18.0


def test_reliability_summary_20_runs():
    """Verify compute_reliability_summary computes accurate metrics for 20 fresh runs."""
    runs = []
    for i in range(20):
        runs.append({
            "sandbox_name": generate_sandbox_name(f"sbx-run{i+1:02d}"),
            "fresh": True,
            "success": i < 18,  # 18 success, 2 failed -> 90%
            "wall_clock_s": round(1.0 + i * 0.1, 2),
            "boot_to_ready_s": 0.5,
            "cost_usd": 0.05,
        })

    summary = compute_reliability_summary(runs)
    assert summary["run_count"] == 20
    assert summary["success_rate"] == 0.9
    assert abs(summary["total_cost_usd"] - 1.0) < 0.01
    assert summary["postmortem_path"] == "reports/postmortem.md"


def test_reject_under_20_runs():
    """Verify compute_reliability_summary raises ValueError when given < 20 runs."""
    runs = [{
        "sandbox_name": generate_sandbox_name(),
        "fresh": True,
        "success": True,
        "wall_clock_s": 1.0,
        "boot_to_ready_s": 0.5,
        "cost_usd": 0.0,
    } for _ in range(15)]

    with pytest.raises(ValueError, match="at least 20 runs"):
        compute_reliability_summary(runs)
