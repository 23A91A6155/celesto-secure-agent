"""Pydantic schemas and request/response models for Celesto Run Ledger API."""

from datetime import datetime
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Allowed Run Lifecycle States
RunState = Literal["created", "ready", "running", "succeeded", "failed", "deleted"]

# Exact Sandbox Regex: ^sbx-[a-z0-9]{8,}$
SANDBOX_NAME_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
EXACT_EXECUTION_TARGET = "celesto_sandbox"


class RunCreateRequest(BaseModel):
    run_id: str = Field(..., min_length=1, description="Unique run identifier")
    sandbox_name: str = Field(..., description="Unique sandbox name matching ^sbx-[a-z0-9]{8,}$")
    problem_id: str = Field(..., min_length=1, description="Identifier of the task or evaluation problem")
    state: RunState = Field(default="created", description="Lifecycle state of the run")
    execution_target: Literal["celesto_sandbox"] = Field(
        default="celesto_sandbox",
        description="Target execution environment, must strictly equal 'celesto_sandbox'",
    )

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("run_id cannot be blank")
        return trimmed

    @field_validator("problem_id")
    @classmethod
    def validate_problem_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("problem_id cannot be blank")
        return trimmed

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not SANDBOX_NAME_REGEX.match(v):
            raise ValueError(
                f"sandbox_name '{v}' is invalid. Must match regex ^sbx-[a-z0-9]{{8,}}$ (lowercase alphanumeric, min 8 chars after 'sbx-')."
            )
        return v

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != EXACT_EXECUTION_TARGET:
            raise ValueError(f"execution_target must strictly equal '{EXACT_EXECUTION_TARGET}'")
        return v


class RunResponse(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class CommandAuditEntry(BaseModel):
    ts: str
    sandbox_name: str
    command: str
    decision: Literal["allow", "block"]
    execution_target: Literal["celesto_sandbox"] = "celesto_sandbox"
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None
    reason: Optional[str] = None
    run_id: Optional[str] = None
    output_digest: Optional[str] = None

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not SANDBOX_NAME_REGEX.match(v):
            raise ValueError(f"sandbox_name '{v}' does not match ^sbx-[a-z0-9]{{8,}}$")
        return v
