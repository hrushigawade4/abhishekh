from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash , make_response
import sqlite3
import os
from datetime import datetime, timedelta
import csv
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas




app = Flask(__name__)
app.secret_key = 'your_secure_secret_key'  # Required for session


DB_PATH = 'bhakts.db'
LANG_FILE = 'translations.json'
SACRED_DATES_FILE = 'sacred_dates.json'

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

def load_sacred_dates():
    with open(SACRED_DATES_FILE, 'r') as f:
        return json.load(f)

def calculate_abhishek_dates(abhishek_type, start_date, duration_months):
    sacred_dates = load_sacred_dates().get(abhishek_type, [])
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = start + timedelta(days=30 * duration_months)
    result = [d for d in sacred_dates if start <= datetime.strptime(d, "%Y-%m-%d") <= end]
    return result

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
        gotra = request.form['gotra']
        abhishek_type = request.form['abhishek_type']
        duration = int(request.form['duration'])
        start = request.form['start_date']
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=30 * duration)
        end = end_dt.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO bhakts (name, gotra, abhishek_type, duration_months, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, gotra, abhishek_type, duration, start, end))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect('bhakts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bhakts")
    bhakts = cursor.fetchall()
    conn.close()

    today = datetime.today().date()

    summary = []
    for row in bhakts:
        end_date = datetime.strptime(row[6], "%Y-%m-%d").date()
        status = "active" if end_date >= today else "expired"
        next_dates = calculate_abhishek_dates(row[3], row[5], row[4])
        summary.append((row[0], row[1], row[3], row[5], next_dates[0] if next_dates else "-", status))

    return render_template('dashboard.html', summary=summary, total=len(bhakts))

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bhakts WHERE id=?", (bhakt_id,))
    b = c.fetchone()
    conn.close()
    if not b:
        return "Not found"
    schedule = calculate_abhishek_dates(b[3], b[5], b[4])
    return render_template('bhakt_detail.html', bhakt=b, schedule=schedule)

@app.route('/calendar')
def calendar():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bhakts")
    rows = c.fetchall()
    conn.close()

    result = {}
    for row in rows:
        bhakt_id = row[0]
        name = row[1]
        abhishek_type = row[3]
        duration = row[4]
        start_date = row[5]
        dates = calculate_abhishek_dates(abhishek_type, start_date, duration)
        
        result[name] = {
            "id": bhakt_id,  # ✅ Add this line
            "abhishek_type": abhishek_type,
            "duration": duration,
            "dates": dates
        }

    return render_template('calendar.html', schedule=result)


@app.route('/export_csv')
def export_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bhakts")
    rows = c.fetchall()
    conn.close()
    path = "backup/bhakts_export.csv"
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Gotra', 'Type', 'Duration', 'Start Date', 'End Date'])
        for r in rows:
            writer.writerow(r[1:])
    return send_file(path, as_attachment=True)

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


if __name__ == "__main__":
    init_db()
    seed_admin()
    app.run(debug=True)
