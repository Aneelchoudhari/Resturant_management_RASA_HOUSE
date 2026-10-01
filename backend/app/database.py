import os
import socket
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:yourpassword@postgres:5432/restaurant_db",
)

if DATABASE_URL.startswith("postgresql"):
    parsed_database_url = urlparse(DATABASE_URL)
    if "@" in parsed_database_url.hostname or parsed_database_url.hostname is None:
        raise RuntimeError(
            "Invalid DATABASE_URL: encode @ in the database password as %40. "
            "The hostname must look like aws-0-<region>.pooler.supabase.com."
        )

try:
    if DATABASE_URL.startswith("postgresql://") and "@postgres" in DATABASE_URL:
        socket.getaddrinfo("postgres", 5432)
except socket.gaierror:
    DATABASE_URL = "sqlite:///./restaurant_local.db"

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
