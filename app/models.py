"""SQLAlchemy ORM models for the Celesto Run Ledger."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunModel(Base):
    __tablename__ = "runs"

    run_id = Column(String(64), primary_key=True, index=True)
    sandbox_name = Column(String(64), nullable=False, index=True)
    problem_id = Column(String(64), nullable=False)
    state = Column(String(32), nullable=False, index=True)
    execution_target = Column(String(32), nullable=False, default="celesto_sandbox")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "sandbox_name": self.sandbox_name,
            "problem_id": self.problem_id,
            "state": self.state,
            "execution_target": self.execution_target,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
