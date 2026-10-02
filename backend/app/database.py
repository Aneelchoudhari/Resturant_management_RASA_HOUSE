import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from app.security_settings import resolve_database_url

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development").lower()
if APP_ENV == "production":
    configured_database_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
else:
    configured_database_url = (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
DATABASE_URL = resolve_database_url(APP_ENV, configured_database_url)

if DATABASE_URL.startswith("postgresql"):
    parsed_database_url = urlparse(DATABASE_URL)
    if "@" in parsed_database_url.hostname or parsed_database_url.hostname is None:
        raise RuntimeError(
            "Invalid DATABASE_URL: encode @ in the database password as %40 "
            "and provide a valid database hostname."
        )

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
