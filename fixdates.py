import sqlite3
from datetime import datetime

DB_PATH = "bhakts.db"  # 🔁 Update this with actual path
DEFAULT_YEAR = 2025
DEFAULT_MONTH = 8  # E.g. assume Panditji meant August

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False

def build_valid_date(day_str):
    """Try to convert a single day value (e.g., '12') to full date string."""
    try:
        day = int(day_str)
        return f"{DEFAULT_YEAR}-{DEFAULT_MONTH:02d}-{day:02d}"
    except:
        return None

def fix_bhakt_dates():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch bhakts
    c.execute("SELECT id, start_date, end_date FROM bhakts")
    rows = c.fetchall()

    fixed_bhakt_updates = []

    for bhakt_id, start_date, end_date in rows:
        new_start = start_date
        new_end = end_date

        # Fix start_date
        if not is_valid_date(start_date):
            corrected = build_valid_date(start_date)
            if corrected:
                print(f"Fixing start_date for ID {bhakt_id}: {start_date} → {corrected}")
                new_start = corrected

        # Fix end_date
        if not is_valid_date(end_date):
            corrected = build_valid_date(end_date)
            if corrected:
                print(f"Fixing end_date for ID {bhakt_id}: {end_date} → {corrected}")
                new_end = corrected

        if new_start != start_date or new_end != end_date:
            fixed_bhakt_updates.append((new_start, new_end, bhakt_id))

    # Apply bhakt date updates
    for start, end, bhakt_id in fixed_bhakt_updates:
        c.execute("UPDATE bhakts SET start_date = ?, end_date = ? WHERE id = ?", (start, end, bhakt_id))

    # Fix completed_abhisheks table
    c.execute("SELECT id, completed_date FROM completed_abhisheks")
    abhi_rows = c.fetchall()
    abhi_updates = []

    for abhi_id, completed_date in abhi_rows:
        if not is_valid_date(completed_date):
            corrected = build_valid_date(completed_date)
            if corrected:
                print(f"Fixing completed_date ID {abhi_id}: {completed_date} → {corrected}")
                abhi_updates.append((corrected, abhi_id))

    for new_date, abhi_id in abhi_updates:
        c.execute("UPDATE completed_abhisheks SET completed_date = ? WHERE id = ?", (new_date, abhi_id))

    conn.commit()
    conn.close()
    print("✅ All dates cleaned and updated.")

if __name__ == "__main__":
    fix_bhakt_dates()
