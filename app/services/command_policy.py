"""Centralized Command Gateway and Security Policy Enforcement.

Every command attempt is audited to logs/commands.jsonl before dispatch.
Unsafe, exfiltration, or host-targeting commands are blocked before reaching
the Celesto microVM execution layer.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Lock
from typing import Optional, Tuple

from app.schemas import SANDBOX_NAME_REGEX, EXACT_EXECUTION_TARGET
from app.config import settings

# Dangerous patterns to block before dispatch
BLOCKED_PATTERNS = [
    # Fork bombs and system resource exhaustion
    (re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"), "Resource exhaustion / fork bomb pattern"),
    # Direct raw disk / filesystem destruction
    (re.compile(r"\bmkfs(\.\w+)?\s+/dev/"), "Raw disk filesystem destruction attempt"),
    (re.compile(r"\bdd\s+if=/dev/(zero|urandom)\s+of=/dev/"), "Raw disk wipe attempt"),
    # Outbound exfiltration vectors
    (re.compile(r"\bcurl\s+.*(-d|--data|-F|--form|-X\s*(POST|PUT)).*https?://", re.IGNORECASE), "Unauthorized outbound data exfiltration via curl"),
    (re.compile(r"\bwget\s+.*--post-(data|file).*https?://", re.IGNORECASE), "Unauthorized outbound data exfiltration via wget"),
    (re.compile(r"\b(nc|netcat|ncat)\s+.*-e\b"), "Reverse shell or netcat payload execution"),
    (re.compile(r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+"), "Bash socket exfiltration attempt"),
    # Reading environment secrets
    (re.compile(r"/proc/(\d+|self)/environ"), "Attempted inspection of process environment secrets"),
    # Host escape indicators
    (re.compile(r"\bchroot\s+/host\b"), "Host filesystem escape indicator"),
    (re.compile(r"\bmount\s+.*(/dev/|/proc|/sys)"), "Unauthorized privileged mount operation"),
]

# Sensitive patterns to sanitize before logging
SECRET_REDACT_PATTERNS = [
    (re.compile(r"(api[_-]?key|password|secret|token)[\s=:]+[\'\"]?([a-zA-Z0-9_\-\.]{8,})[\'\"]?", re.IGNORECASE), r"\1=***REDACTED***"),
    (re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{16,})", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "sk-***REDACTED***"),
]

_audit_lock = Lock()


class CommandGateway:
    def __init__(self, log_path: str = "logs/commands.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def sanitize_command(self, command: str) -> str:
        """Strip sensitive credentials from command text before audit logging."""
        sanitized = command
        for pattern, replacement in SECRET_REDACT_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    def evaluate(self, sandbox_name: str, command: str) -> Tuple[bool, str]:
        """Evaluate command against security policy. Returns (allowed, reason)."""
        if not SANDBOX_NAME_REGEX.match(sandbox_name):
            return False, f"Invalid sandbox name format: '{sandbox_name}'"

        if not command or not command.strip():
            return False, "Command cannot be empty"

        if len(command) > settings.MAX_COMMAND_LENGTH:
            return False, f"Command exceeds maximum permitted length of {settings.MAX_COMMAND_LENGTH} characters"

        # Check against blocked threat patterns
        for pattern, reason in BLOCKED_PATTERNS:
            if pattern.search(command):
                return False, f"Command blocked by policy: {reason}"

        return True, "Permitted by command policy"

    def audit_entry(
        self,
        sandbox_name: str,
        command: str,
        decision: str,
        reason: str,
        run_id: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        output_digest: Optional[str] = None,
    ) -> dict:
        """Construct and write a verified audit entry to logs/commands.jsonl."""
        sanitized_cmd = self.sanitize_command(command)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sandbox_name": sandbox_name,
            "command": sanitized_cmd,
            "decision": decision,
            "execution_target": EXACT_EXECUTION_TARGET,
            "reason": reason,
            "run_id": run_id or "run-unknown",
            "exit_code": exit_code,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "output_digest": output_digest,
        }

        line = json.dumps(entry, separators=(",", ":"))
        with _audit_lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        return entry

    def execute_with_policy(
        self,
        sandbox_name: str,
        command: str,
        run_id: str,
        executor_func,
    ) -> dict:
        """Central dispatch: evaluates policy, audits attempt, dispatches if allowed."""
        is_allowed, reason = self.evaluate(sandbox_name, command)

        if not is_allowed:
            # Audit the blocked attempt BEFORE returning
            audit = self.audit_entry(
                sandbox_name=sandbox_name,
                command=command,
                decision="block",
                reason=reason,
                run_id=run_id,
                exit_code=126,  # Standard policy deny exit code
                duration_ms=0.0,
            )
            return {
                "success": False,
                "exit_code": 126,
                "stdout": "",
                "stderr": f"SECURITY_POLICY_BLOCK: {reason}",
                "blocked": True,
                "reason": reason,
                "audit": audit,
            }

        # Permitted command: execute through provided Celesto executor
        start_time = datetime.now(timezone.utc)
        result = executor_func(sandbox_name, command)
        elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0

        exit_code = result.get("exit_code", 0)
        output_str = result.get("stdout", "") + result.get("stderr", "")
        digest = hashlib.sha256(output_str.encode("utf-8")).hexdigest()[:16] if output_str else None

        audit = self.audit_entry(
            sandbox_name=sandbox_name,
            command=command,
            decision="allow",
            reason="Command executed inside isolated Celesto sandbox",
            run_id=run_id,
            exit_code=exit_code,
            duration_ms=elapsed_ms,
            output_digest=digest,
        )

        result["audit"] = audit
        result["blocked"] = False
        return result


command_gateway = CommandGateway()
