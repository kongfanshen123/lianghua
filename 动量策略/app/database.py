from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from app.config import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class SessionContextManager:
    def __enter__(self):
        self.session = SessionLocal()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        self.session.close()


def session_scope():
    return SessionContextManager()


def init_db():
    from app.models import Symbol, DailyPrice, StrategyResult
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    # Migration: add consecutive_days column if not exists
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE strategy_results ADD COLUMN consecutive_days INTEGER DEFAULT 0"))
            conn.commit()
    except Exception:
        pass  # Column already exists
