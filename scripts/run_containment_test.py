"""Script to execute the deliberate containment test and generate evidence."""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.containment import ContainmentTestRunner


def main():
    print("--- Executing Celesto Containment & Prompt Injection Exfiltration Test ---")
    runner = ContainmentTestRunner()
    result = runner.run_containment_test()
    print(f"Result: {result}")
    if result["blocked"] and result["host_untouched"]:
        print("PASS: Adversarial exfiltration attempt blocked and host integrity verified.")
        return 0
    else:
        print("FAIL: Containment test failed to verify safety invariants.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
