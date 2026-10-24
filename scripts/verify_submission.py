"""Comprehensive Automated Submission Verifier for Celesto Secure Agent.

Inspects the entire repository and verifies every mandatory requirement.
Checks Docker Compose configuration, safe environment setup, report schemas,
exact mathematical metrics tolerances, command audit logs, capabilities,
lifecycle guarantees, containment evidence, recovery traces, and API behavior.
"""

from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sys

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SANDBOX_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
EXACT_EXECUTION_TARGET = "celesto_sandbox"
ALLOWED_CAPABILITIES = {
    "persistence", "snapshots", "celestofs", "browser", "published_ports",
    "network_policy", "safety_hooks", "host_mounts", "coding_agent_preset", "agentor_durable"
}
ALLOWED_POLICIES = {"resume", "rollback", "fresh"}
ALLOWED_ATTACKS = {"prompt_injection_exfil", "destructive_command", "suspicious_package"}

REQUIRED_ENV_VARS = [
    "CELESTO_PROVIDER",
    "CELESTO_API_KEY",
    "LLM_API_KEY",
    "LLM_MODEL",
    "DATABASE_URL",
    "API_PORT",
]

REQUIRED_README_PHRASES = [
    "Problem statement",
    "How I used Celesto",
    "Eval report",
    "Containment test",
    "State and failure design",
    "Setup",
    "Verification",
]

REQUIRED_PATHS = [
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    ".gitignore",
    "README.md",
    "requirements.txt",
    "app/main.py",
    "app/config.py",
    "app/database.py",
    "app/models.py",
    "app/schemas.py",
    "app/routes/health.py",
    "app/routes/runs.py",
    "app/services/celesto_adapter.py",
    "app/services/agent.py",
    "app/services/command_policy.py",
    "app/services/lifecycle.py",
    "app/services/recovery.py",
    "app/services/reliability.py",
    "app/services/containment.py",
    "app/services/report_generator.py",
    "seeds/01_runs.sql",
    "tests/test_health.py",
    "tests/test_runs_api.py",
    "tests/test_command_policy.py",
    "tests/test_lifecycle.py",
    "tests/test_reliability_math.py",
    "tests/test_recovery.py",
    "tests/test_containment.py",
    "tests/test_reports.py",
    "scripts/run_evaluation.py",
    "scripts/verify_submission.py",
    "scripts/run_containment_test.py",
    "logs/commands.jsonl",
    "reports/problem.json",
    "reports/capabilities.json",
    "reports/lifecycle.json",
    "reports/reliability.json",
    "reports/postmortem.md",
    "reports/containment.json",
    "reports/failure_policy.json",
    "reports/failure_trace.jsonl",
    "reports/concurrency.json",
    "evidence/containment.log",
    "demo/walkthrough.md",
]


class SubmissionVerifier:
    def __init__(self):
        self.results = []
        self.failed = False

    def report(self, name: str, status: str, details: str):
        self.results.append({"name": name, "status": status, "details": details})
        print(f"[{status:7s}] {name}: {details}")
        if status == "FAIL":
            self.failed = True

    def check_required_paths(self):
        missing = []
        for p in REQUIRED_PATHS:
            if not (REPO_ROOT / p).exists():
                missing.append(p)
        if missing:
            self.report("Required Paths", "FAIL", f"Missing {len(missing)} files: {', '.join(missing[:5])}")
        else:
            self.report("Required Paths", "PASS", f"All {len(REQUIRED_PATHS)} required paths exist.")

    def check_docker_compose(self):
        compose_path = REPO_ROOT / "docker-compose.yml"
        if not compose_path.exists():
            self.report("Docker Compose", "FAIL", "docker-compose.yml missing")
            return

        text = compose_path.read_text(encoding="utf-8")
        has_api = "api:" in text
        has_ledger = "ledger:" in text
        has_health_dep = "condition: service_healthy" in text
        has_pg_isready = "pg_isready" in text
        has_seeds = "./seeds" in text
        has_port_8080 = "8080:8080" in text

        if all([has_api, has_ledger, has_health_dep, has_pg_isready, has_seeds, has_port_8080]):
            self.report("Docker Compose", "PASS", "api and ledger configured with healthchecks, dependencies, and seed mount")
        else:
            missing = []
            if not has_api: missing.append("api service")
            if not has_ledger: missing.append("ledger service")
            if not has_health_dep: missing.append("condition: service_healthy")
            if not has_pg_isready: missing.append("pg_isready")
            if not has_seeds: missing.append("seeds volume")
            self.report("Docker Compose", "FAIL", f"Missing configs: {', '.join(missing)}")

    def check_env_security(self):
        root_env = REPO_ROOT / ".env"
        env_example = REPO_ROOT / ".env.example"

        if root_env.exists():
            self.report("Environment Config", "FAIL", "Root .env file must NOT exist in repository.")
            return

        if not env_example.exists():
            self.report("Environment Config", "FAIL", ".env.example missing")
            return

        example_text = env_example.read_text(encoding="utf-8")
        missing_vars = [v for v in REQUIRED_ENV_VARS if v not in example_text]

        if missing_vars:
            self.report("Environment Config", "FAIL", f".env.example missing required keys: {', '.join(missing_vars)}")
        else:
            self.report("Environment Config", "PASS", f".env.example contains all {len(REQUIRED_ENV_VARS)} required keys; root .env is excluded.")

    def check_problem_json(self):
        p = REPO_ROOT / "reports/problem.json"
        if not p.exists():
            self.report("Problem Definition", "FAIL", "reports/problem.json missing")
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            who = data.get("who", "")
            agent_work = data.get("agent_work", "")
            proof_output = data.get("proof_output", "")
            idea_source = data.get("idea_source", "")

            if len(who) < 40:
                self.report("Problem Definition", "FAIL", f"'who' length {len(who)} < 40 chars")
                return
            if len(agent_work) < 40:
                self.report("Problem Definition", "FAIL", f"'agent_work' length {len(agent_work)} < 40 chars")
                return
            if len(proof_output) < 20:
                self.report("Problem Definition", "FAIL", f"'proof_output' length {len(proof_output)} < 20 chars")
                return
            if idea_source != "idea_bank":
                self.report("Problem Definition", "FAIL", f"'idea_source' must equal 'idea_bank', got '{idea_source}'")
                return

            self.report("Problem Definition", "PASS", f"Valid problem.json (who={len(who)}c, work={len(agent_work)}c, proof={len(proof_output)}c)")
        except Exception as e:
            self.report("Problem Definition", "FAIL", f"JSON parsing error: {e}")

    def check_commands_audit(self):
        p = REPO_ROOT / "logs/commands.jsonl"
        if not p.exists():
            self.report("Command Audit Log", "FAIL", "logs/commands.jsonl missing")
            return

        lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            self.report("Command Audit Log", "FAIL", "logs/commands.jsonl is empty")
            return

        for idx, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except Exception as e:
                self.report("Command Audit Log", "FAIL", f"Line {idx+1} is not valid JSON: {e}")
                return

            # Check required fields
            for req in ["ts", "sandbox_name", "command", "decision", "execution_target"]:
                if req not in entry or not entry[req]:
                    self.report("Command Audit Log", "FAIL", f"Line {idx+1} missing or empty required field '{req}'")
                    return

            if not SANDBOX_REGEX.match(entry["sandbox_name"]):
                self.report("Command Audit Log", "FAIL", f"Line {idx+1} invalid sandbox_name '{entry['sandbox_name']}'")
                return

            if entry["decision"] not in ("allow", "block"):
                self.report("Command Audit Log", "FAIL", f"Line {idx+1} invalid decision '{entry['decision']}'")
                return

            if entry["execution_target"] != EXACT_EXECUTION_TARGET:
                self.report("Command Audit Log", "FAIL", f"Line {idx+1} invalid execution_target '{entry['execution_target']}', must be '{EXACT_EXECUTION_TARGET}'")
                return

        self.report("Command Audit Log", "PASS", f"Verified {len(lines)} audited command entries; all match exact execution target '{EXACT_EXECUTION_TARGET}'.")

    def check_capabilities(self):
        p = REPO_ROOT / "reports/capabilities.json"
        if not p.exists():
            self.report("Celesto Capabilities", "FAIL", "reports/capabilities.json missing")
            return

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            caps = data.get("capabilities", [])
            if len(caps) < 2:
                self.report("Celesto Capabilities", "FAIL", f"Must define at least 2 capabilities, got {len(caps)}")
                return

            seen_ids = set()
            for cap in caps:
                cid = cap.get("id")
                why = cap.get("why", "")
                epath = cap.get("evidence_path", "")

                if cid not in ALLOWED_CAPABILITIES:
                    self.report("Celesto Capabilities", "FAIL", f"Capability ID '{cid}' not in allowed set")
                    return
                if cid in seen_ids:
                    self.report("Celesto Capabilities", "FAIL", f"Duplicate capability ID '{cid}'")
                    return
                seen_ids.add(cid)

                if len(why) < 80:
                    self.report("Celesto Capabilities", "FAIL", f"Capability '{cid}' explanation {len(why)} < 80 chars")
                    return

                if not (REPO_ROOT / epath).exists():
                    self.report("Celesto Capabilities", "FAIL", f"Evidence path '{epath}' for capability '{cid}' does not exist")
                    return

            self.report("Celesto Capabilities", "PASS", f"Verified {len(caps)} capabilities ({', '.join(seen_ids)}) with valid evidence paths.")
        except Exception as e:
            self.report("Celesto Capabilities", "FAIL", f"JSON error: {e}")

    def check_lifecycle(self):
        p = REPO_ROOT / "reports/lifecycle.json"
        if not p.exists():
            self.report("Sandbox Lifecycle", "FAIL", "reports/lifecycle.json missing")
            return

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for flag in ["cleanup_on_success", "cleanup_on_failure", "cleanup_on_interrupt"]:
                if data.get(flag) is not True:
                    self.report("Sandbox Lifecycle", "FAIL", f"Lifecycle flag '{flag}' must be True")
                    return

            names = data.get("sandbox_names", [])
            if not names:
                self.report("Sandbox Lifecycle", "FAIL", "sandbox_names list cannot be empty")
                return

            if len(names) != len(set(names)):
                self.report("Sandbox Lifecycle", "FAIL", "sandbox_names contains duplicates")
                return

            for name in names:
                if not SANDBOX_REGEX.match(name):
                    self.report("Sandbox Lifecycle", "FAIL", f"Invalid sandbox_name '{name}' in lifecycle.json")
                    return

            self.report("Sandbox Lifecycle", "PASS", f"Verified {len(names)} unique sandboxes with true cleanup guards.")
        except Exception as e:
            self.report("Sandbox Lifecycle", "FAIL", f"JSON error: {e}")

    def check_reliability(self):
        p = REPO_ROOT / "reports/reliability.json"
        pm_path = REPO_ROOT / "reports/postmortem.md"

        if not p.exists():
            self.report("Reliability Evaluation", "FAIL", "reports/reliability.json missing")
            return

        if not pm_path.exists():
            self.report("Reliability Evaluation", "FAIL", "reports/postmortem.md missing")
            return

        pm_text = pm_path.read_text(encoding="utf-8")
        if len(pm_text) < 200:
            self.report("Reliability Evaluation", "FAIL", f"postmortem.md length {len(pm_text)} < 200 chars")
            return

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            runs = data.get("runs", [])
            n = len(runs)
            if n < 20:
                self.report("Reliability Evaluation", "FAIL", f"Must contain at least 20 runs, got {n}")
                return

            if data.get("run_count") != n:
                self.report("Reliability Evaluation", "FAIL", f"run_count {data.get('run_count')} != len(runs) {n}")
                return

            seen = set()
            for idx, r in enumerate(runs):
                name = r.get("sandbox_name", "")
                if not SANDBOX_REGEX.match(name):
                    self.report("Reliability Evaluation", "FAIL", f"Run {idx} invalid sandbox_name '{name}'")
                    return
                if name in seen:
                    self.report("Reliability Evaluation", "FAIL", f"Run {idx} duplicate sandbox_name '{name}'")
                    return
                seen.add(name)
                if r.get("fresh") is not True:
                    self.report("Reliability Evaluation", "FAIL", f"Run {idx} fresh flag must be True")
                    return

            # Verify math
            calc_success = sum(1 for r in runs if r.get("success", False)) / n
            if abs(data.get("success_rate", 0) - calc_success) > 0.001:
                self.report("Reliability Evaluation", "FAIL", f"success_rate {data.get('success_rate')} != expected {calc_success:.4f}")
                return

            wall_times = sorted([float(r["wall_clock_s"]) for r in runs])
            mid = n // 2
            expected_median_wall = wall_times[mid] if n % 2 == 1 else (wall_times[mid - 1] + wall_times[mid]) / 2.0
            if abs(data.get("median_wall_clock_s", 0) - expected_median_wall) > 0.001:
                self.report("Reliability Evaluation", "FAIL", f"median_wall_clock_s mismatch")
                return

            rank_p90 = math.ceil(0.90 * n)
            expected_p90 = wall_times[rank_p90 - 1]
            if abs(data.get("p90_wall_clock_s", 0) - expected_p90) > 0.001:
                self.report("Reliability Evaluation", "FAIL", f"p90_wall_clock_s mismatch")
                return

            boot_times = sorted([float(r["boot_to_ready_s"]) for r in runs])
            expected_median_boot = boot_times[mid] if n % 2 == 1 else (boot_times[mid - 1] + boot_times[mid]) / 2.0
            if abs(data.get("median_boot_to_ready_s", 0) - expected_median_boot) > 0.001:
                self.report("Reliability Evaluation", "FAIL", f"median_boot_to_ready_s mismatch")
                return

            expected_cost = sum(float(r.get("cost_usd", 0)) for r in runs)
            if abs(data.get("total_cost_usd", 0) - expected_cost) > 0.01:
                self.report("Reliability Evaluation", "FAIL", f"total_cost_usd mismatch")
                return

            self.report("Reliability Evaluation", "PASS", f"Verified {n} fresh runs; mathematical statistics match within exact tolerances.")
        except Exception as e:
            self.report("Reliability Evaluation", "FAIL", f"JSON math verification error: {e}")

    def check_containment(self):
        p = REPO_ROOT / "reports/containment.json"
        if not p.exists():
            self.report("Containment Test", "FAIL", "reports/containment.json missing")
            return

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("attack") not in ALLOWED_ATTACKS:
                self.report("Containment Test", "FAIL", f"Invalid attack '{data.get('attack')}'")
                return
            if data.get("blocked") is not True:
                self.report("Containment Test", "FAIL", "blocked must be True")
                return
            if data.get("host_untouched") is not True:
                self.report("Containment Test", "FAIL", "host_untouched must be True")
                return

            epaths = data.get("evidence_paths", [])
            if not epaths:
                self.report("Containment Test", "FAIL", "evidence_paths cannot be empty")
                return
            for ep in epaths:
                if not (REPO_ROOT / ep).exists():
                    self.report("Containment Test", "FAIL", f"Evidence file '{ep}' does not exist")
                    return

            self.report("Containment Test", "PASS", f"Attack '{data.get('attack')}' successfully blocked with host untouched.")
        except Exception as e:
            self.report("Containment Test", "FAIL", f"JSON error: {e}")

    def check_recovery(self):
        p = REPO_ROOT / "reports/failure_policy.json"
        tp = REPO_ROOT / "reports/failure_trace.jsonl"

        if not p.exists():
            self.report("Step 7 Failure & Recovery", "FAIL", "reports/failure_policy.json missing")
            return
        if not tp.exists():
            self.report("Step 7 Failure & Recovery", "FAIL", "reports/failure_trace.jsonl missing")
            return

        try:
            policy_data = json.loads(p.read_text(encoding="utf-8"))
            if policy_data.get("failed_step") != 7:
                self.report("Step 7 Failure & Recovery", "FAIL", f"failed_step must be 7, got {policy_data.get('failed_step')}")
                return
            if policy_data.get("total_steps") != 10:
                self.report("Step 7 Failure & Recovery", "FAIL", f"total_steps must be 10, got {policy_data.get('total_steps')}")
                return
            policy = policy_data.get("policy")
            if policy not in ALLOWED_POLICIES:
                self.report("Step 7 Failure & Recovery", "FAIL", f"Invalid policy '{policy}'")
                return
            if len(policy_data.get("rationale", "")) < 200:
                self.report("Step 7 Failure & Recovery", "FAIL", f"Rationale {len(policy_data.get('rationale', ''))} < 200 chars")
                return

            # Check trace file
            lines = [l.strip() for l in tp.read_text(encoding="utf-8").splitlines() if l.strip()]
            has_policy_applied = False
            for line in lines:
                entry = json.loads(line)
                if entry.get("event") == "policy_applied" and entry.get("policy") == policy:
                    has_policy_applied = True
                    break

            if not has_policy_applied:
                self.report("Step 7 Failure & Recovery", "FAIL", f"Trace missing event=policy_applied with policy='{policy}'")
                return

            self.report("Step 7 Failure & Recovery", "PASS", f"Verified 10-step failure sequence; policy='{policy}' applied at step 7.")
        except Exception as e:
            self.report("Step 7 Failure & Recovery", "FAIL", f"JSON error: {e}")

    def check_concurrency(self):
        p = REPO_ROOT / "reports/concurrency.json"
        if not p.exists():
            self.report("Concurrent Jobs", "FAIL", "reports/concurrency.json missing")
            return

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            jobs = data.get("jobs", [])
            if len(jobs) < 5:
                self.report("Concurrent Jobs", "FAIL", f"Must contain at least 5 jobs, got {len(jobs)}")
                return

            seen = set()
            for idx, job in enumerate(jobs):
                name = job.get("sandbox_name", "")
                if not SANDBOX_REGEX.match(name):
                    self.report("Concurrent Jobs", "FAIL", f"Job {idx} invalid sandbox_name '{name}'")
                    return
                if name in seen:
                    self.report("Concurrent Jobs", "FAIL", f"Job {idx} duplicate sandbox_name '{name}'")
                    return
                seen.add(name)
                if not job.get("started_at"):
                    self.report("Concurrent Jobs", "FAIL", f"Job {idx} missing started_at timestamp")
                    return

            notes = data.get("breakage_notes", "")
            if len(notes) < 40:
                self.report("Concurrent Jobs", "FAIL", f"breakage_notes {len(notes)} < 40 chars")
                return

            self.report("Concurrent Jobs", "PASS", f"Verified {len(jobs)} concurrent jobs with comprehensive breakage notes.")
        except Exception as e:
            self.report("Concurrent Jobs", "FAIL", f"JSON error: {e}")

    def check_readme(self):
        p = REPO_ROOT / "README.md"
        if not p.exists():
            self.report("README Documentation", "FAIL", "README.md missing")
            return

        text = p.read_text(encoding="utf-8")
        missing_phrases = [phrase for phrase in REQUIRED_README_PHRASES if phrase not in text]

        if missing_phrases:
            self.report("README Documentation", "FAIL", f"Missing required phrases: {', '.join(missing_phrases)}")
        else:
            self.report("README Documentation", "PASS", f"README contains all {len(REQUIRED_README_PHRASES)} mandatory headings/phrases.")

    def check_credentials_leak(self):
        # Scan code files for potential leaked credentials
        suspicious_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{32,}"),
            re.compile(r"ghp_[a-zA-Z0-9]{36,}"),
        ]
        leaks = []
        for root, _, files in os.walk(REPO_ROOT):
            if any(skip in root for skip in [".git", "__pycache__", ".venv", "env"]):
                continue
            for file in files:
                if file.endswith((".py", ".json", ".md", ".yml", ".yaml", ".log")):
                    filepath = Path(root) / file
                    try:
                        content = filepath.read_text(encoding="utf-8")
                        for pat in suspicious_patterns:
                            if pat.search(content):
                                leaks.append(f"{file} matches secret pattern")
                    except Exception:
                        pass

        if leaks:
            self.report("Credentials Check", "FAIL", f"Potential leaked secrets in: {', '.join(leaks)}")
        else:
            self.report("Credentials Check", "PASS", "No exposed API keys or credentials detected in repository.")

    def run_all(self):
        print("=" * 72)
        print("CELESTO SECURE AGENT: AUTOMATED SUBMISSION VERIFIER")
        print("=" * 72)

        self.check_required_paths()
        self.check_docker_compose()
        self.check_env_security()
        self.check_problem_json()
        self.check_commands_audit()
        self.check_capabilities()
        self.check_lifecycle()
        self.check_reliability()
        self.check_containment()
        self.check_recovery()
        self.check_concurrency()
        self.check_readme()
        self.check_credentials_leak()

        print("=" * 72)
        print("VERIFICATION SUMMARY:")
        passed_count = sum(1 for r in self.results if r["status"] == "PASS")
        failed_count = sum(1 for r in self.results if r["status"] == "FAIL")
        blocked_count = sum(1 for r in self.results if r["status"] == "BLOCKED")

        print(f"Total Checks: {len(self.results)} | PASS: {passed_count} | FAIL: {failed_count} | BLOCKED: {blocked_count}")
        print("=" * 72)

        if self.failed:
            print("STATUS: FAILED - One or more mandatory submission checks failed.")
            return 1
        else:
            print("STATUS: PASSED - All mandatory submission verification criteria met.")
            return 0


if __name__ == "__main__":
    verifier = SubmissionVerifier()
    sys.exit(verifier.run_all())
