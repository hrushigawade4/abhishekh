from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash , make_response
import sqlite3
import os
from datetime import datetime, timedelta, date
import csv
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from dateutil.relativedelta import relativedelta




app = Flask(__name__)
app.secret_key = 'your_secure_secret_key'  # Required for session


DB_PATH = 'bhakts.db'
LANG_FILE = 'translations.json'
SACRED_DATES_FILE = 'sacred_dates.json'
SACRED_JSON_PATH = 'sacred_dates.json'

def is_logged_in():
    return 'user' in session

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bhakts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            gotra TEXT,
            abhishek_type TEXT,
            duration_months INTEGER,
            start_date TEXT,
            end_date TEXT
        )
    """)
    # ✅ NEW TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS completed_abhisheks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bhakt_id INTEGER,
            abhishek_type TEXT,
            completed_date TEXT
        )
    """)
    conn.commit()
    conn.close()


def seed_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", "admin123", "admin"))
        conn.commit()
    conn.close()

ABHISHEK_TYPES_FILE = 'abhishek_types.json'



@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pw))
        data = c.fetchone()
        conn.close()
        if data:
            session['user'] = user
            session['role'] = data[3]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        address = request.form['address']
        email = request.form['email']
        gotra = request.form['gotra']
        abhishek_type = request.form['type']
        duration = int(request.form['duration'])
        start = request.form['start_date']

        # ✅ Validate date
        if not validate_date(start):
            flash("❌ Invalid start date. Please use YYYY-MM-DD format.")
            return redirect(url_for('register'))

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=30 * duration)
        end = end_dt.strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO bhakts 
            (name, mobile, address, email, gotra, abhishek_type, duration_months, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, mobile, address, email, gotra, abhishek_type, duration, start, end))
        conn.commit()
        conn.close()

        flash("✅ Bhakt registered successfully.")
        return redirect(url_for('dashboard'))

    # Load available abhishek types from sacred_dates.json
    abhishek_data = load_sacred_dates()
    abhishek_types = sorted(abhishek_data.keys())
    return render_template('register.html', abhishek_types=abhishek_types)


def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False


def safe_parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


 # install via pip if not present

@app.route("/dashboard")
def dashboard():
    today = datetime.today()

    # Load sacred_dates.json
    with open("sacred_dates.json", "r", encoding="utf-8") as f:
        sacred_data = json.load(f)

    conn = sqlite3.connect("bhakts.db")
    c = conn.cursor()

    c.execute("SELECT id, name, abhishek_type, start_date, duration_months FROM bhakts")
    bhakts = c.fetchall()

    summary = []
    next_month_abhisheks = []
    total = len(bhakts)

    for b in bhakts:
        bhakt_id, name, abhishek_type, start_date, duration = b
        start_stripped = start_date or "-"
        start_hint = ""
        next_hint = ""

        # Safe date parsing
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            start = today  # fallback if malformed

        # Calculate end date
        try:
            duration = int(duration)
            end = start + timedelta(days=30 * duration)
        except:
            end = start + timedelta(days=365)  # fallback duration

        # Default status
        status = "active" if today <= end else "expired"

        # Next Abhishek
        next_abhishek = "Not Scheduled"
        if abhishek_type in sacred_data:
            for date_str in sacred_data[abhishek_type]:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if start <= dt <= end:
                        next_abhishek = dt.strftime("%Y-%m-%d")
                        next_hint = dt.strftime("%A, %d %b %Y")
                        break
                except:
                    continue

        # Hint format
        start_hint = start.strftime("%A, %d %b %Y") if start else ""

        summary.append([
            bhakt_id,
            name,
            abhishek_type,
            start_date,
            next_abhishek,
            status,
            next_hint,
            start_hint
        ])

        # Check if next_abhishek is in next month
        if next_abhishek and next_abhishek != "Not Scheduled":
            try:
                dt = datetime.strptime(next_abhishek, "%Y-%m-%d")
                if dt.month == (today.month % 12 + 1) and dt.year == (today.year if today.month < 12 else today.year + 1):
                    next_month_abhisheks.append([
                        bhakt_id,
                        name,
                        abhishek_type,
                        start_date,
                        next_abhishek
                    ])
            except:
                pass

    conn.close()

    return render_template("dashboard.html",
                           summary=summary,
                           total=total,
                           next_month_abhisheks=next_month_abhisheks)





def safe_parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except:
        return False





def add_sacred_date(abhishek_type, new_date):
    abhishek_type = abhishek_type.strip()
    new_date = new_date.strip()

    with open('sacred_dates.json', 'r') as f:
        data = json.load(f)

    # ✅ Append date only if it’s not already present
    if abhishek_type in data:
        if new_date and new_date not in data[abhishek_type]:
            data[abhishek_type].append(new_date)
    else:
        # ✅ If new type not in JSON, create it
        data[abhishek_type] = [new_date]

    with open('sacred_dates.json', 'w') as f:
        json.dump(data, f, indent=2)



@app.route('/search')
def search():
    q = request.args.get('q', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bhakts WHERE name LIKE ?", ('%' + q + '%',))
    results = c.fetchall()
    conn.close()
    return render_template('search.html', results=results, q=q)

@app.route('/bhakt/<int:bhakt_id>')
def bhakt_detail(bhakt_id):
    # Safely open the DB connection
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM bhakts WHERE id = ?", (bhakt_id,))
        b = c.fetchone()

    if not b:
        return "भक्त सापडला नाही." , 404  # Marathi fallback or message

    # Load sacred dates JSON
    with open(SACRED_JSON_PATH, 'r', encoding='utf-8') as f:
        sacred_data = json.load(f)

    # Extract bhakt fields
    name, gotra, abhishek_type = b[1], b[2], b[3]
    duration, start_date, end_date = b[4], b[5], b[6]

    # Get enriched abhishek schedule
    schedule = get_enriched_dates(abhishek_type, duration, start_date, bhakt_id, sacred_data)

    # Completion counts
    completed = sum(1 for d in schedule if d.get("completed"))
    remaining = len(schedule) - completed

    return render_template(
        'bhakt_detail.html',
        bhakt=b,
        schedule=schedule,
        completed=completed,
        remaining=remaining
    )




@app.route('/calendar')
def calendar():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM bhakts")
    rows = c.fetchall()

    c.execute("SELECT bhakt_id, abhishek_type, completed_date FROM completed_abhisheks")
    completed_raw = c.fetchall()
    conn.close()

    completed = set((row[0], row[1], row[2]) for row in completed_raw)

    today = date.today()
    next_week = today + timedelta(days=7)
    next_month = today + timedelta(days=30)

    groups = {
        "Upcoming This Week": {},
        "Next Month": {},
        "Completed Only": {}
    }

    for row in rows:
        bhakt_id = row[0]
        name = row[1]
        abhishek_type = row[3]
        duration = row[4]
        start_date = row[5]

        dates = calculate_abhishek_dates(abhishek_type, start_date, duration)

        completed_dates = [d for d in dates if (bhakt_id, abhishek_type, d) in completed]
        upcoming_dates = [
            d for d in dates
            if datetime.strptime(d, '%Y-%m-%d').date() >= today
            and d not in completed_dates
        ]

        enriched_dates = []
        for d in dates:
            d_date = datetime.strptime(d, '%Y-%m-%d').date()
            delta = (d_date - today).days
            enriched_dates.append({
                "date": d,
                "delta": delta,
                "completed": (bhakt_id, abhishek_type, d) in completed
            })

        bhakt_info = {
            "id": bhakt_id,
            "abhishek_type": abhishek_type,
            "duration": duration,
            "enriched_dates": enriched_dates,
            "completed": completed_dates,
            "upcoming": upcoming_dates
        }


        if not upcoming_dates:
            groups["Completed Only"][name] = bhakt_info
        else:
            next_abhishek = datetime.strptime(upcoming_dates[0], '%Y-%m-%d').date()
            if next_abhishek <= next_week:
                groups["Upcoming This Week"][name] = bhakt_info
            elif next_abhishek <= next_month:
                groups["Next Month"][name] = bhakt_info
            else:
                groups["Completed Only"][name] = bhakt_info

    return render_template('calendar.html', schedule=groups, now=datetime.now())




@app.route('/export_csv')
def export_csv():
    import os
    import tempfile

    bhakt_type = request.args.get('type', 'all')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bhakts")
    rows = c.fetchall()
    conn.close()

    with open(SACRED_JSON_PATH, 'r') as f:
        sacred_data = json.load(f)

    today = datetime.today().date()
    first_day_next_month = today.replace(day=1) + relativedelta(months=1)
    last_day_next_month = first_day_next_month + relativedelta(months=1) - timedelta(days=1)

    filtered_rows = []

    for r in rows:
        try:
            bhakt_id = r[0]
            name, gotra, abhishek_type, duration, start_date_raw, end_date_raw = r[1:7]

            # 🔧 Ensure string for date parsing
            start_date_str = str(start_date_raw)
            end_date_str = str(end_date_raw)

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception:
            continue  # Skip malformed row

        status = "active" if end_date >= today else "expired"

        try:
            next_dates = calculate_abhishek_dates(abhishek_type, duration, start_date_str)
            next_abhishek = next_dates[0] if next_dates else None
        except Exception:
            next_abhishek = None

        if bhakt_type == 'active' and status != 'active':
            continue
        if bhakt_type == 'expired' and status != 'expired':
            continue
        if bhakt_type == 'next_month':
            if not next_abhishek or not (first_day_next_month <= next_abhishek.date() <= last_day_next_month):
                continue

        filtered_rows.append((r, next_abhishek))

    # 🔧 Prepare CSV
    os.makedirs("backup", exist_ok=True)
    export_path = os.path.join("backup", f"bhakts_export_{bhakt_type}.csv")

    with open(export_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Gotra', 'Type', 'Duration', 'Start Date', 'End Date', 'Next Abhishek', 'Completed', 'Remaining'])

        for r, next_abhishek in filtered_rows:
            bhakt_id = r[0]
            name, gotra, abhishek_type, duration, start_date, end_date = r[1:7]

            # 🔧 Defensive date strings
            start_date_str = str(start_date)
            end_date_str = str(end_date)

            enriched_dates = get_enriched_dates(abhishek_type, duration, start_date_str, bhakt_id, sacred_data)
            completed = sum(1 for d in enriched_dates if d["completed"])
            remaining = len(enriched_dates) - completed

            writer.writerow([
                name, gotra, abhishek_type, duration,
                start_date_str, end_date_str,
                next_abhishek.strftime("%Y-%m-%d") if next_abhishek else "-",
                completed, remaining
            ])

    return send_file(export_path, as_attachment=True)




def get_enriched_dates(abhishek_type, duration, start_date_str, bhakt_id, sacred_data):
    sacred_dates = sacred_data.get(abhishek_type, [])
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    all_dates = [
        datetime.strptime(d, "%Y-%m-%d")
        for d in sacred_dates
        if start_date <= datetime.strptime(d, "%Y-%m-%d") <= start_date + relativedelta(months=+int(duration))
    ]

    # Get completed dates from DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT completed_date FROM completed_abhisheks WHERE bhakt_id=? AND abhishek_type=?", (bhakt_id, abhishek_type))

    completed_dates = {row[0] for row in c.fetchall()}
    conn.close()

    enriched = []
    for d in all_dates:
        date_str = d.strftime("%Y-%m-%d")
        delta = (d.date() - datetime.today().date()).days
        enriched.append({
            "date": date_str,
            "delta": delta,
            "completed": date_str in completed_dates
        })
    return enriched


# @app.route('/receipt/<int:bhakt_id>/<abhishek_type>')
# def generate_receipt(bhakt_id, abhishek_type):
#     # Load bhakt info
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("SELECT name, gotra FROM bhakts WHERE id = ?", (bhakt_id,))
#     bhakt = c.fetchone()
#     conn.close()

#     if not bhakt:
#         return "Bhakt not found", 404

#     # Create PDF
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#     p.setFont("Helvetica-Bold", 14)

#     p.drawString(100, 800, "🕉️ Shri Mandir Abhishek Receipt")
#     p.setFont("Helvetica", 12)
#     p.drawString(100, 770, f"Name: {bhakt[0]}")
#     p.drawString(100, 750, f"Gotra: {bhakt[1]}")
#     p.drawString(100, 730, f"Abhishek Type: {abhishek_type}")
#     p.drawString(100, 710, f"Date: {datetime.today().strftime('%d-%b-%Y')}")
#     p.drawString(100, 690, f"Status: ✅ Completed Successfully")

#     p.line(90, 675, 500, 675)
#     p.drawString(100, 650, "🙏 Thank you for your Seva. May your devotion be blessed.")

#     p.showPage()
#     p.save()

#     buffer.seek(0)
#     return send_file(buffer, as_attachment=True, download_name=f"{bhakt[0]}_{abhishek_type}_receipt.pdf", mimetype='application/pdf')


@app.route('/receipt/<int:bhakt_id>/<abhishek_type>')
def generate_receipt(bhakt_id, abhishek_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, start_date, duration FROM bhakts WHERE id=?", (bhakt_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "Bhakt not found"

    name, start_date, duration = row
    all_dates = calculate_abhishek_dates(abhishek_type, start_date, duration)

    from datetime import datetime
    today = datetime.today().date()
    abhishek_date = next((d for d in all_dates if datetime.strptime(d, "%Y-%m-%d").date() >= today), "N/A")

    return render_template("receipt.html",
                           bhakt_name=name,
                           abhishek_type=abhishek_type,
                           abhishek_date=abhishek_date)

@app.route('/mark_completed', methods=['POST'])
def mark_completed():
        bhakt_id = request.form['bhakt_id']
        abhishek_type = request.form['abhishek_type']
        completed_date = request.form['date']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO completed_abhisheks (bhakt_id, abhishek_type, completed_date) VALUES (?, ?, ?)",
                (bhakt_id, abhishek_type, completed_date))
        conn.commit()
        conn.close()
        return redirect(url_for('calendar'))

def get_today_tomorrow_reminders():
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, id FROM bhakts")
    bhakts = c.fetchall()
    reminders_today = 0
    reminders_tomorrow = 0

    for b in bhakts:
        dates = calculate_abhishek_dates(...)  # use your existing logic
        if today in dates:
            reminders_today += 1
        if tomorrow in dates:
            reminders_tomorrow += 1

    return reminders_today, reminders_tomorrow

@app.route('/sacred_dates', methods=['GET', 'POST'])
def sacred_dates():
    if request.method == 'POST':
        selected_type = request.form.get("abhishek_type", "").strip()
        new_type_input = request.form.get("new_abhishek_type", "").strip()
        new_date = request.form.get("new_date", "").strip()

        if new_type_input:
            save_abhishek_type(new_type_input)
            selected_type = new_type_input

        if selected_type and new_date:
            add_sacred_date(selected_type, new_date)
            flash(f"✅ {selected_type} - {new_date} added as sacred date.")

    # Load types and dates
    abhishek_types = list(load_abhishek_types().keys())
    with open('sacred_dates.json', 'r') as f:
        sacred = json.load(f)

    return render_template('sacred_dates.html', abhishek_types=abhishek_types, sacred_dates=sacred)


@app.template_filter('todatetime')
def to_datetime_filter(value, fmt='%Y-%m-%d'):
    return datetime.strptime(value, fmt)

@app.context_processor
def inject_now():
    return {'now': lambda: datetime.now()}

@app.template_filter('todatetime')
def to_datetime_filter(value, fmt='%Y-%m-%d'):
    if isinstance(value, datetime):
        return value  # already datetime
    return datetime.strptime(value, fmt)

def load_sacred_dates():
    with open(ABHISHEK_TYPES_FILE, 'r') as f:
        return json.load(f)


def load_abhishek_types():
    with open(ABHISHEK_TYPES_FILE, 'r') as f:
        return json.load(f)  # ✅ Returns list


def save_abhishek_type(new_type):
    new_type = new_type.strip()

    # Load list of types
    with open(ABHISHEK_TYPES_FILE, 'r') as f:
        types = json.load(f)

    if new_type and new_type not in types:
        types.append(new_type)

        # Save updated types list
        with open(ABHISHEK_TYPES_FILE, 'w') as f:
            json.dump(types, f, indent=2)

        # Also update sacred_dates.json dict with new empty entry
        with open(SACRED_DATES_FILE, 'r') as f:
            dates = json.load(f)

        if new_type not in dates:
            dates[new_type] = []

        with open(SACRED_DATES_FILE, 'w') as f:
            json.dump(dates, f, indent=2)







def calculate_abhishek_dates(abhishek_type, start_date_str, duration_months):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    try:
        duration_months = int(duration_months)
    except (ValueError, TypeError):
        return []

    try:
        end_date = start_date + relativedelta(months=duration_months)
    except Exception:
        return []

    # Load sacred dates from JSON
    try:
        with open("sacred_dates.json", "r", encoding="utf-8") as f:
            sacred_data = json.load(f)
    except Exception:
        return []

    if abhishek_type not in sacred_data:
        return []

    upcoming_dates = []

    for date_str in sacred_data[abhishek_type]:
        try:
            sacred_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if start_date <= sacred_date <= end_date:
                upcoming_dates.append(sacred_date.strftime("%Y-%m-%d"))
        except Exception:
            continue

    upcoming_dates.sort()  # sort ascending
    return upcoming_dates



if __name__ == "__main__":
    init_db()
    seed_admin()
    app.run(debug=True)
