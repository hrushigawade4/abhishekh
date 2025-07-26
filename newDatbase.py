import sqlite3

conn = sqlite3.connect("bhakts.db")
c = conn.cursor()

# Create bhakts table
c.execute("""
CREATE TABLE bhakts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT,
    address TEXT,
    abhishek_type TEXT,
    start_date TEXT,
    end_date TEXT,
    duration_months INTEGER,
    email TEXT,
    gotra TEXT
)
""")

conn.commit()
conn.close()
print("✅ New database created with bhakts table.")
