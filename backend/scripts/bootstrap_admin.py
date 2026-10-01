"""Create or promote the first application admin in the configured database.

Run from backend/ after setting DATABASE_URL or SUPABASE_DATABASE_URL:
    python scripts/bootstrap_admin.py --email admin@example.com --password "..." --name "Admin"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models
from app.auth import hash_password
from app.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap an application admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        staff = db.query(models.Staff).filter(models.Staff.email == args.email).first()
        if staff:
            staff.name = args.name
            staff.role = models.StaffRole.admin
            staff.hashed_password = hash_password(args.password)
            action = "promoted"
        else:
            staff = models.Staff(
                name=args.name,
                email=args.email,
                role=models.StaffRole.admin,
                hashed_password=hash_password(args.password),
            )
            db.add(staff)
            action = "created"
        db.commit()
        print(f"Admin account {action}: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
