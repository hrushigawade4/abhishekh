import sqlite3

conn = sqlite3.connect('bhakts.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS completed_abhisheks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bhakt_id INTEGER,
  abhishek_type TEXT,
  completed_date TEXT
)
''')

conn.commit()
conn.close()

print("✅ completed_abhisheks table created successfully.")

