-- Schema and Seed initialization for Celesto Run Ledger
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(64) PRIMARY KEY,
    sandbox_name VARCHAR(64) NOT NULL,
    problem_id VARCHAR(64) NOT NULL,
    state VARCHAR(32) NOT NULL,
    execution_target VARCHAR(32) NOT NULL DEFAULT 'celesto_sandbox',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_execution_target CHECK (execution_target = 'celesto_sandbox'),
    CONSTRAINT check_state CHECK (state IN ('created', 'ready', 'running', 'succeeded', 'failed', 'deleted'))
);

CREATE INDEX IF NOT EXISTS idx_runs_sandbox_name ON runs(sandbox_name);
CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state);

-- Idempotent initial seed row
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
VALUES (
    'run-seed-0001',
    'sbx-seeddemo1',
    'celesto-agent-task',
    'deleted',
    'celesto_sandbox'
)
ON CONFLICT (run_id) DO UPDATE SET
    sandbox_name = EXCLUDED.sandbox_name,
    problem_id = EXCLUDED.problem_id,
    state = EXCLUDED.state,
    execution_target = EXCLUDED.execution_target,
    updated_at = CURRENT_TIMESTAMP;
