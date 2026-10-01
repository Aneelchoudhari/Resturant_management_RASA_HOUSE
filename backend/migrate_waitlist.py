import sqlalchemy as sa

# Add missing columns to waitlist_entries
engine = sa.create_engine("sqlite:///restaurant_local.db")

with engine.connect() as conn:
    # Check if columns exist first
    inspector = sa.inspect(engine)
    cols = [c['name'] for c in inspector.get_columns('waitlist_entries')]
    print('Current columns:', cols)
    
    if 'customer_id' not in cols:
        conn.execute(sa.text('ALTER TABLE waitlist_entries ADD COLUMN customer_id INTEGER REFERENCES customers(id)'))
        print('Added customer_id')
    else:
        print('customer_id already exists')
    
    if 'entry_type' not in cols:
        conn.execute(sa.text("ALTER TABLE waitlist_entries ADD COLUMN entry_type VARCHAR NOT NULL DEFAULT 'walk_in'"))
        print('Added entry_type')
    else:
        print('entry_type already exists')
    
    conn.commit()
    print('Migration complete')
