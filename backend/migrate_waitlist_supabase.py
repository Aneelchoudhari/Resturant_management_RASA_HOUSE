"""
Migration script: add customer_id and entry_type to waitlist_entries on the live Supabase DB.
"""
import os
import sys
sys.path.insert(0, '.')
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: SUPABASE_DATABASE_URL not set")
    sys.exit(1)

print("Connecting to configured database")
engine = sa.create_engine(DATABASE_URL)

with engine.connect() as conn:
    inspector = sa.inspect(engine)
    cols = [c['name'] for c in inspector.get_columns('waitlist_entries')]
    print('Current waitlist_entries columns:', cols)

    if 'customer_id' not in cols:
        conn.execute(sa.text(
            'ALTER TABLE waitlist_entries ADD COLUMN customer_id INTEGER REFERENCES customers(id)'
        ))
        print('Added: customer_id')
    else:
        print('Skipped: customer_id already exists')

    if 'entry_type' not in cols:
        conn.execute(sa.text(
            "ALTER TABLE waitlist_entries ADD COLUMN entry_type VARCHAR NOT NULL DEFAULT 'walk_in'"
        ))
        print('Added: entry_type')
    else:
        print('Skipped: entry_type already exists')

    conn.commit()
    print('Migration complete!')

engine.dispose()
