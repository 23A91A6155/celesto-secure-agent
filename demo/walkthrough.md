# Celesto Secure AI Agent: Demonstration & Verification Walkthrough

This walkthrough guides reviewers through deploying the Trusted Control Plane, executing the agent within Celesto sandboxes, observing safety containment, triggering failure recovery at step 7, and inspecting the PostgreSQL run ledger.

---

## 1. Prerequisites and Environment Setup

Ensure Python 3.11+ and Docker Desktop / Docker Compose are available.

```bash
# Clone or navigate to the repository
cd c:/celesto-secure-agent

# Install dependencies in your active Python environment
pip install -r requirements.txt

# Inspect safe environment defaults
# Note: Root .env must NOT be committed to version control
cp .env.example .env.local
```

---

## 2. Starting the Trusted Control Plane (Docker Compose)

Start the PostgreSQL Run Ledger and FastAPI Control Plane services:

```bash
# Start API and PostgreSQL ledger in the background
docker compose up -d --build

# Wait for healthchecks to become healthy
docker compose ps
```

Verify service health via the liveness probe:

```bash
# Should return HTTP 200 {"status":"ok"}
curl -i http://localhost:8080/health
```

---

## 3. Querying the PostgreSQL Run Ledger

The database automatically initializes its schema and seeds the initial demo record:

```bash
# Retrieve all recorded runs (includes seeded sbx-seeddemo1)
curl -s http://localhost:8080/api/runs
```

Test inserting a valid new run into the ledger:

```bash
curl -X POST http://localhost:8080/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "run-demo-001",
    "sandbox_name": "sbx-demorun1234",
    "problem_id": "celesto-agent-task",
    "state": "running",
    "execution_target": "celesto_sandbox"
  }'
```

Verify that invalid requests (such as targeting `host` or invalid sandbox regex) are rejected with HTTP 400:

```bash
# This request MUST return HTTP 400 Bad Request
curl -i -X POST http://localhost:8080/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "run-bad-001",
    "sandbox_name": "sbx-demorun1234",
    "problem_id": "celesto-agent-task",
    "state": "running",
    "execution_target": "host"
  }'
```

---

## 4. Running the Reliability Evaluation (20 Fresh Sandboxes)

Execute the 20-run evaluation harness and snapshot recovery sequence:

```bash
python scripts/run_evaluation.py
```

This script:
1. Provisions 20 fresh sandboxes (`fresh=True`), enforcing collision-resistant naming (`^sbx-[a-z0-9]{8,}$`).
2. Audits every command attempt to `logs/commands.jsonl`.
3. Measures boot-to-ready latency and wall-clock execution with monotonic clocks.
4. Executes the 10-step failure recovery workflow (injecting failure at step 7 and applying `rollback`).
5. Generates `reports/reliability.json` and updates `reports/postmortem.md`.

---

## 5. Running the Adversarial Containment Test

Simulate a prompt-injection exfiltration attack using an isolated canary token:

```bash
python scripts/run_containment_test.py
```

Observe the verification outcome:
- Command Gateway blocks the exfiltration vector before dispatch (`blocked: true`).
- Host-side sentinel file is verified unmodified (`host_untouched: true`).
- Detailed audit logs are written to `reports/evidence/containment.log`.

---

## 6. Comprehensive Automated Verification

Execute the automated submission verifier to validate all 12 project requirements:

```bash
python scripts/verify_submission.py
```

The verifier will inspect:
- Docker Compose service definitions, healthchecks, and mounts.
- Environment security and secret exclusion.
- All report JSON schemas, exact mathematical tolerances, and character thresholds.
- Append-only audit integrity in `logs/commands.jsonl`.
- Host integrity and containment evidence.
- Presence of all required repository paths and documentation phrases.
