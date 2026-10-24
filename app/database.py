"""Database engine, session factory, and startup initialization for Celesto Run Ledger."""

import logging
from typing import Generator
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.models import Base, RunModel

logger = logging.getLogger("celesto.database")

def _initialize_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    connect_args = {"connect_timeout": 2} if "postgresql" in db_url else {}
    if "postgresql" in db_url:
        try:
            cand_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                echo=False,
                connect_args=connect_args,
            )
            # Test connectivity immediately
            with cand_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL ledger database.")
            return cand_engine
        except Exception as e:
            logger.warning(
                f"PostgreSQL at {db_url} is not reachable ({e}). "
                "Falling back to local SQLite ledger (sqlite:///./celesto_ledger_local.db) for local execution."
            )
            fallback_engine = create_engine(
                "sqlite:///./celesto_ledger_local.db",
                connect_args={"check_same_thread": False},
            )
            return fallback_engine
    else:
        return create_engine(db_url, connect_args={"check_same_thread": False})


engine = _initialize_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Immediately ensure tables and seed row exist for the initialized engine
try:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as _session:
        _seed = _session.get(RunModel, "run-seed-0001")
        if not _seed:
            _session.add(
                RunModel(
                    run_id="run-seed-0001",
                    sandbox_name="sbx-seeddemo1",
                    problem_id="celesto-agent-task",
                    state="deleted",
                    execution_target="celesto_sandbox",
                )
            )
            _session.commit()
except Exception as _e:
    logger.warning(f"Immediate schema initialization deferred: {_e}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Initialize database tables and ensure idempotent seed row exists."""
    global engine, SessionLocal
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
    except Exception as e:
        if target_engine is None and "sqlite" not in str(eng.url):
            logger.warning(f"Engine connection failed during init_db: {e}. Switching to SQLite.")
            engine = create_engine(
                "sqlite:///./celesto_ledger_local.db",
                connect_args={"check_same_thread": False},
            )
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            init_db(target_engine=engine)
        else:
            logger.error(f"Database error during initialization: {e}")
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
