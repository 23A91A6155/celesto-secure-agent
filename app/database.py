"""Database engine, session factory, and startup initialization for Celesto Run Ledger."""

import logging
from typing import Generator
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.models import Base, RunModel

logger = logging.getLogger("celesto.database")

# Normalize database URL
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    # Convert standard postgresql:// to postgresql+psycopg:// if using psycopg v3
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"connect_timeout": 2} if "postgresql" in db_url else {}
try:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        echo=False,
        connect_args=connect_args,
    )
except Exception as e:
    logger.warning(f"Failed to create engine with {db_url}: {e}. Falling back to sqlite for testing.")
    engine = create_engine("sqlite:///./celesto_ledger_local.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Initialize database tables and ensure idempotent seed row exists."""
    eng = target_engine or engine
    try:
        # Create tables
        Base.metadata.create_all(bind=eng)
        logger.info("Database schema initialized successfully.")

        # Ensure seed row exists idempotently
        with Session(eng) as session:
            seed_row = session.get(RunModel, "run-seed-0001")
            if not seed_row:
                seed = RunModel(
                    run_id="run-seed-0001",
                    sandbox_name="sbx-seeddemo1",
                    problem_id="celesto-agent-task",
                    state="deleted",
                    execution_target="celesto_sandbox",
                )
                session.add(seed)
                session.commit()
                logger.info("Seeded initial run: sbx-seeddemo1 (run-seed-0001).")
            else:
                # Update existing seed row if needed
                seed_row.sandbox_name = "sbx-seeddemo1"
                seed_row.state = "deleted"
                seed_row.execution_target = "celesto_sandbox"
                session.commit()
    except OperationalError as oe:
        logger.error(f"Database operational error during initialization: {oe}")
        raise


def check_db_health(target_engine=None) -> bool:
    """Verify database connectivity."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
