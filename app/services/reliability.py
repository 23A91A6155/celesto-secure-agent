"""Reliability Evaluation and Statistical Metrics Engine.

Computes exact statistical metrics (median, p90, success rate, cost) across
at least 20 fresh sandbox execution records adhering strictly to the required
mathematical specifications and tolerances.
"""

import math
from pathlib import Path
from typing import Dict, List, Tuple
from app.schemas import SANDBOX_NAME_REGEX


def compute_median(values: List[float]) -> float:
    """Compute median from sorted observations.

    For even counts, averages the two central values.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    else:
        return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)


def compute_p90(values: List[float]) -> float:
    """Compute p90 as the sorted observation at 1-based rank ceil(0.90 * n)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # 1-based rank
    rank = math.ceil(0.90 * n)
    idx = max(0, min(rank - 1, n - 1))
    return float(sorted_vals[idx])


def compute_reliability_summary(runs: List[Dict[str, any]]) -> Dict[str, any]:
    """Calculate summary statistics from run rows with strict numerical precision.

    Validates:
    - len(runs) >= 20
    - All runs fresh=True
    - Unique sandbox names matching ^sbx-[a-z0-9]{8,}$
    """
    n = len(runs)
    if n < 20:
        raise ValueError(f"Reliability evaluation requires at least 20 runs, but received {n}.")

    seen_names = set()
    for idx, r in enumerate(runs):
        name = r.get("sandbox_name", "")
        if not SANDBOX_NAME_REGEX.match(name):
            raise ValueError(f"Run {idx} has invalid sandbox_name '{name}'")
        if name in seen_names:
            raise ValueError(f"Run {idx} contains duplicate sandbox_name '{name}'")
        seen_names.add(name)

        if not r.get("fresh", False):
            raise ValueError(f"Run {idx} ('{name}') must have fresh=True")

    successful_runs = sum(1 for r in runs if r.get("success", False))
    success_rate = round(successful_runs / n, 4)

    wall_times = [float(r["wall_clock_s"]) for r in runs]
    boot_times = [float(r["boot_to_ready_s"]) for r in runs]
    costs = [float(r.get("cost_usd", 0.0)) for r in runs]

    median_wall = round(compute_median(wall_times), 4)
    p90_wall = round(compute_p90(wall_times), 4)
    median_boot = round(compute_median(boot_times), 4)
    total_cost = round(sum(costs), 4)

    return {
        "run_count": n,
        "runs": runs,
        "success_rate": success_rate,
        "median_wall_clock_s": median_wall,
        "p90_wall_clock_s": p90_wall,
        "median_boot_to_ready_s": median_boot,
        "total_cost_usd": total_cost,
        "postmortem_path": "reports/postmortem.md",
    }
