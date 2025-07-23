import sqlite3

DB_PATH = "bhakts.db"  # or the correct relative path

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check if 'duration' column exists
    cursor.execute("PRAGMA table_info(bhakts)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'duration' not in columns:
        cursor.execute("ALTER TABLE bhakts ADD COLUMN duration INTEGER DEFAULT 12")
        print("✅ 'duration' column added successfully.")
    else:
        print("ℹ️ 'duration' column already exists.")
except Exception as e:
    print("❌ Error during migration:", e)

conn.commit()
conn.close()
