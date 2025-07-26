import sqlite3
from datetime import datetime

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False

conn = sqlite3.connect("bhakts.db")
cursor = conn.cursor()

cursor.execute("SELECT id, start_date, end_date FROM bhakts")
rows = cursor.fetchall()

for row in rows:
    bhakt_id, start_date, end_date = row
    updated = False

    # Fix start_date
    if not is_valid_date(start_date):
        print(f"[FIX] Bhakt ID {bhakt_id} has invalid start_date: {start_date}")
        new_start = "2024-01-01"  # or ask user
        cursor.execute("UPDATE bhakts SET start_date = ? WHERE id = ?", (new_start, bhakt_id))
        updated = True

    # Fix end_date
    if not is_valid_date(end_date):
        print(f"[FIX] Bhakt ID {bhakt_id} has invalid end_date: {end_date}")
        new_end = "2024-12-31"  # or ask user
        cursor.execute("UPDATE bhakts SET end_date = ? WHERE id = ?", (new_end, bhakt_id))
        updated = True

    if updated:
        print(f"✔ Updated Bhakt ID {bhakt_id}")

conn.commit()
conn.close()
print("✅ Cleanup complete.")
