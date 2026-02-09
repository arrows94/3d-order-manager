from __future__ import annotations

import os
from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine

def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:////data/app.db")

engine = create_engine(get_database_url(), echo=False)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

@contextmanager
def session_scope():
    with Session(engine) as session:
        yield session
