import os
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///veritas_ledger.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    """Initializes tables if they do not already exist and applies lightweight schema migrations."""
    SQLModel.metadata.create_all(engine)

    # Automatic schema migration & high-concurrency WAL mode for SQLite
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                # Enable WAL (Write-Ahead Logging) for high-concurrency 100+ users
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))

                result = conn.execute(text("PRAGMA table_info(claim_records)")).fetchall()
                existing_cols = {row[1] for row in result}

                if "canonical_claim" not in existing_cols:
                    conn.execute(text("ALTER TABLE claim_records ADD COLUMN canonical_claim TEXT"))
                if "is_duplicate_of" not in existing_cols:
                    conn.execute(text("ALTER TABLE claim_records ADD COLUMN is_duplicate_of TEXT"))
                conn.commit()
        except Exception:
            pass

def get_session():
    """FastAPI dependency yielding a database session."""
    with Session(engine) as session:
        yield session
