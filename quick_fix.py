import sqlite3


def quick_fix_schema():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    try:
        # Check current schema
        c.execute("PRAGMA table_info(seat_availability)")
        columns = c.fetchall()
        print("Current schema:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # Add schedule_id column if it doesn't exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='seat_availability'")
        if c.fetchone():
            try:
                c.execute("ALTER TABLE seat_availability ADD COLUMN schedule_id INTEGER")
                print("✅ Added schedule_id column")
            except Exception as e:
                print(f"⚠️ schedule_id column might already exist: {e}")

        conn.commit()
        print("✅ Database schema updated successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    quick_fix_schema()