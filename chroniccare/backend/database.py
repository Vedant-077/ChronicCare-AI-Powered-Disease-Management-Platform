# database.py
# This file sets up the connection to our database.
# Right now we use SQLite (a single file, "chroniccare.db") — great for
# local development. To switch to PostgreSQL later, you'd only change
# the DATABASE_URL line below (e.g. "postgresql://user:pass@host/dbname").

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./chroniccare.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}  # only needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    This function gives each API request its own database session,
    and makes sure it's closed afterward. FastAPI will call this
    automatically wherever we ask for it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
