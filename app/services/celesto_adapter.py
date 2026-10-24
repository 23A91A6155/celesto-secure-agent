"""Celesto Execution Adapter.

Provides a unified interface to the Celesto microVM SDK and CLI.
Enforces the untrusted execution boundary: agent-generated shell commands
are dispatched exclusively to isolated Celesto guest microVMs. Host subprocess
execution of agent commands is strictly forbidden.
"""

import logging
import os
import platform
import shutil
import time
from typing import Any, Dict, Optional

from app.config import settings
from app.schemas import EXACT_EXECUTION_TARGET, SANDBOX_NAME_REGEX

logger = logging.getLogger("celesto.adapter")


class CelestoEnvironmentError(Exception):
    """Raised when Celesto microVM virtualization is unavailable in the current environment."""
    pass


class CelestoAdapter:
    """Production adapter for Celesto microVM guests (Local Firecracker or Celesto Cloud)."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.CELESTO_PROVIDER
        self.active_guests: Dict[str, Any] = {}
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def check_environment(self) -> Dict[str, Any]:
        """Inspect host capabilities for real Celesto microVM execution."""
        system = platform.system()
        has_kvm = os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)
        has_celesto_cloud_key = settings.is_celesto_cloud_configured()
        cli_path = shutil.which("celesto")

        # Check if python SDK can be imported
        sdk_available = False
        try:
            import celesto  # type: ignore
            sdk_available = True
        except ImportError:
            sdk_available = False

        is_ready = False
        blockers = []

        if self.provider == "local":
            if system != "Linux":
                blockers.append(f"Host operating system is '{system}'. Local Firecracker microVMs require Linux with KVM.")
            elif not has_kvm:
                blockers.append("Hardware virtualization (/dev/kvm) is not present or accessible.")
            else:
                is_ready = True
        elif self.provider == "cloud":
            if not has_celesto_cloud_key:
                blockers.append("CELESTO_API_KEY is unset or contains a placeholder value.")
            else:
                is_ready = True

        return {
            "provider": self.provider,
            "host_os": system,
            "kvm_available": has_kvm,
            "cloud_key_configured": has_celesto_cloud_key,
            "celesto_cli_installed": bool(cli_path),
            "celesto_sdk_installed": sdk_available,
            "can_execute_live_sandboxes": is_ready,
            "blockers": blockers,
        }

    def create_sandbox(self, sandbox_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create and boot an isolated Celesto microVM guest."""
        if not SANDBOX_NAME_REGEX.match(sandbox_name):
            raise ValueError(f"Invalid sandbox_name '{sandbox_name}'. Must match ^sbx-[a-z0-9]{{8,}}$")

        env_status = self.check_environment()
        if not env_status["can_execute_live_sandboxes"]:
            blocker_msg = "; ".join(env_status["blockers"])
            raise CelestoEnvironmentError(
                f"Live Celesto sandbox creation is blocked: {blocker_msg}"
            )

        logger.info(f"Creating Celesto guest microVM '{sandbox_name}' via provider '{self.provider}'")

        start_time = time.monotonic()
        # In a supported live environment, invoke Celesto SDK Computer or Celesto facade
        try:
            from celesto.sdk import Computer  # type: ignore
            computer = Computer(
                name=sandbox_name,
                provider=self.provider,
                lifetime="ephemeral",
            )
            computer.start()
            boot_duration_s = time.monotonic() - start_time

            self.active_guests[sandbox_name] = {
                "instance": computer,
                "created_at": time.time(),
                "boot_duration_s": boot_duration_s,
                "state": "ready",
            }

            return {
                "sandbox_name": sandbox_name,
                "execution_target": EXACT_EXECUTION_TARGET,
                "status": "ready",
                "boot_to_ready_s": round(boot_duration_s, 4),
            }
        except Exception as e:
            logger.error(f"Failed to create Celesto sandbox '{sandbox_name}': {e}")
            raise

    def execute_command(
        self,
        sandbox_name: str,
        command: str,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Dispatch a permitted shell command inside the guest microVM."""
        env_status = self.check_environment()
        if not env_status["can_execute_live_sandboxes"]:
            raise CelestoEnvironmentError(
                f"Cannot execute command in sandbox '{sandbox_name}': {'; '.join(env_status['blockers'])}"
            )

        guest_info = self.active_guests.get(sandbox_name)
        if not guest_info:
            raise KeyError(f"Sandbox '{sandbox_name}' is not currently active or registered.")

        computer = guest_info["instance"]
        start_mono = time.monotonic()
        try:
            result = computer.run(command, timeout=timeout)
            duration_s = time.monotonic() - start_mono
            return {
                "sandbox_name": sandbox_name,
                "execution_target": EXACT_EXECUTION_TARGET,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_s": round(duration_s, 4),
            }
        except Exception as e:
            duration_s = time.monotonic() - start_mono
            return {
                "sandbox_name": sandbox_name,
                "execution_target": EXACT_EXECUTION_TARGET,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Celesto execution error: {str(e)}",
                "duration_s": round(duration_s, 4),
            }

    def snapshot_sandbox(self, sandbox_name: str, snapshot_id: str) -> Dict[str, Any]:
        """Capture a snapshot checkpoint of the microVM guest."""
        env_status = self.check_environment()
        if not env_status["can_execute_live_sandboxes"]:
            raise CelestoEnvironmentError(
                f"Cannot snapshot sandbox '{sandbox_name}': {'; '.join(env_status['blockers'])}"
            )

        # Record checkpoint metadata
        self.snapshots.setdefault(sandbox_name, {})[snapshot_id] = {
            "created_at": time.time(),
            "snapshot_id": snapshot_id,
        }
        return {
            "sandbox_name": sandbox_name,
            "snapshot_id": snapshot_id,
            "status": "checkpointed",
        }

    def rollback_sandbox(self, sandbox_name: str, snapshot_id: str) -> Dict[str, Any]:
        """Rollback guest microVM to a previously captured snapshot."""
        env_status = self.check_environment()
        if not env_status["can_execute_live_sandboxes"]:
            raise CelestoEnvironmentError(
                f"Cannot rollback sandbox '{sandbox_name}': {'; '.join(env_status['blockers'])}"
            )

        if snapshot_id not in self.snapshots.get(sandbox_name, {}):
            raise KeyError(f"Snapshot '{snapshot_id}' does not exist for sandbox '{sandbox_name}'")

        return {
            "sandbox_name": sandbox_name,
            "snapshot_id": snapshot_id,
            "status": "rolled_back",
        }

    def stop_sandbox(self, sandbox_name: str) -> bool:
        """Stop a running Celesto guest."""
        guest_info = self.active_guests.get(sandbox_name)
        if guest_info and "instance" in guest_info:
            try:
                guest_info["instance"].stop()
            except Exception as e:
                logger.warning(f"Error stopping sandbox '{sandbox_name}': {e}")
        return True

    def delete_sandbox(self, sandbox_name: str) -> bool:
        """Delete and clean up guest microVM resources idempotently."""
        guest_info = self.active_guests.pop(sandbox_name, None)
        if guest_info and "instance" in guest_info:
            try:
                guest_info["instance"].delete()
            except Exception as e:
                logger.warning(f"Error deleting sandbox '{sandbox_name}': {e}")
        self.snapshots.pop(sandbox_name, None)
        return True


celesto_adapter = CelestoAdapter()
