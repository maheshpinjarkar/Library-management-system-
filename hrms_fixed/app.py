from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from datetime import date, datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-prod")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# 🔥 UPLOAD FOLDER SETUP
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_theme():
    data = {"theme": session.get("theme", "Purple")}
    if 'admin' in session:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'")
            data["notif_count"] = cursor.fetchone()[0]
            conn.close()
        except Exception:
            data["notif_count"] = 0
    return data


# 🔥 DATABASE INIT
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # EMPLOYEES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        name TEXT,
        dob TEXT,
        gender TEXT,
        job_title TEXT,
        department TEXT,
        joining_date TEXT,
        employment_type TEXT,
        manager TEXT,
        location TEXT,
        email TEXT,
        phone TEXT,
        emergency TEXT,
        status TEXT,
        kyc TEXT,
        profile TEXT
    )
    """)

    # ATTENDANCE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        name TEXT,
        date TEXT,
        status TEXT
    )
    """)

    # PAYROLL
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payroll (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        name TEXT,
        basic REAL,
        bonus REAL,
        deduction REAL,
        total REAL,
        date TEXT
    )
    """)

    # NOTIFICATIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        status TEXT DEFAULT 'unread',
        date TEXT
    )
    """)

    # ADMIN
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        name TEXT,
        email TEXT,
        theme TEXT DEFAULT 'Purple'
    )
    """)

    # Older DB migration: add missing columns safely
    cursor.execute("PRAGMA table_info(admin)")
    cols = [r[1] for r in cursor.fetchall()]
    if "name" not in cols:
        cursor.execute("ALTER TABLE admin ADD COLUMN name TEXT")
    if "email" not in cols:
        cursor.execute("ALTER TABLE admin ADD COLUMN email TEXT")
    if "theme" not in cols:
        cursor.execute("ALTER TABLE admin ADD COLUMN theme TEXT DEFAULT 'Purple'")

    cursor.execute("SELECT * FROM admin")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admin (username, password, name, email, theme) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("1234"), "Admin", "admin@example.com", "Purple"),
        )

    conn.commit()
    conn.close()

init_db()


# 🔐 LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id, username, password, theme FROM admin WHERE username=?", (username,))
        admin = cursor.fetchone()

        ok = False
        if admin:
            stored = admin[2] or ""
            # Backward compatible: accept old plaintext and auto-upgrade to hash
            if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
                ok = check_password_hash(stored, password or "")
            else:
                ok = (stored == (password or ""))
                if ok and password:
                    cursor.execute(
                        "UPDATE admin SET password=? WHERE id=?",
                        (generate_password_hash(password), admin[0]),
                    )
                    conn.commit()
        conn.close()

        if ok:
            session['admin'] = username
            session['theme'] = (admin[3] if admin and admin[3] else "Purple")
            return redirect("/")
        else:
            return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")


# 🚪 LOGOUT
@app.route("/logout")
def logout():
    session.pop('admin', None)
    return redirect("/login")


# 🏠 🔥 REAL DASHBOARD
@app.route("/")
@login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 👥 EMPLOYEES
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_emp = cursor.fetchone()[0]

    # 🏢 DEPARTMENTS
    cursor.execute("SELECT COUNT(DISTINCT department) FROM employees")
    total_dept = cursor.fetchone()[0]

    # 💰 SALARY
    cursor.execute("SELECT SUM(total) FROM payroll")
    total_salary = cursor.fetchone()[0] or 0

    # 📊 ATTENDANCE
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'")
    present = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Absent'")
    absent = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Leave'")
    leave = cursor.fetchone()[0]

    # 📊 DEPARTMENT GRAPH
    cursor.execute("SELECT department, COUNT(*) FROM employees GROUP BY department")
    dept_data = cursor.fetchall()

    # 🔔 NOTIFICATIONS
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'")
    notif_count = cursor.fetchone()[0]

    # ✅ Extra dashboard widgets (template expects these)
    cursor.execute("SELECT COUNT(*) FROM employees WHERE status='Active'")
    active_emp = cursor.fetchone()[0]

    today = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'", (today,))
    absent_today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Leave'", (today,))
    on_leave = cursor.fetchone()[0]

    # Joining date is stored as text (usually YYYY-MM-DD). We'll treat last 30 days as "new joiners".
    cursor.execute(
        "SELECT COUNT(*) FROM employees WHERE joining_date >= date('now','-30 day') AND joining_date != ''"
    )
    new_join = cursor.fetchone()[0]

    # Top salary + gender + hiring trend charts
    cursor.execute("SELECT name, total FROM payroll ORDER BY total DESC LIMIT 5")
    top_salary = cursor.fetchall()

    cursor.execute("SELECT gender, COUNT(*) FROM employees GROUP BY gender")
    gender_data = cursor.fetchall()

    cursor.execute(
        "SELECT substr(joining_date,1,7) as ym, COUNT(*) FROM employees "
        "WHERE joining_date != '' GROUP BY substr(joining_date,1,7) ORDER BY ym"
    )
    hiring_data = cursor.fetchall()

    # 📈 Attendance Trend (Last 7 days) - for "Performance" chart (real data)
    labels = []
    values = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        labels.append(d[5:])  # MM-DD
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'", (d,))
        values.append(cursor.fetchone()[0])

    conn.close()

    return render_template("dashboard.html",
        total_emp=total_emp,
        total_dept=total_dept,
        total_salary=total_salary,
        present=present,
        absent=absent,
        leave=leave,
        dept_data=dept_data,
        notif_count=notif_count,
        active_emp=active_emp,
        absent_today=absent_today,
        on_leave=on_leave,
        new_join=new_join,
        top_salary=top_salary,
        gender_data=gender_data,
        hiring_data=hiring_data,
        perf_labels=labels,
        perf_values=values,
    )


# ➕ ADD EMPLOYEE
@app.route("/add_employee", methods=["GET", "POST"])
@login_required
def add_employee():
    if request.method == "POST":
        emp_id = request.form.get('emp_id')
        name = request.form.get('name')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        job = request.form.get('job_title')
        dept = request.form.get('department')
        join = request.form.get('joining_date')
        emp_type = request.form.get('employment_type')
        manager = request.form.get('manager')
        location = request.form.get('location')
        email = request.form.get('email')
        phone = request.form.get('phone')
        emergency = request.form.get('emergency')
        status = request.form.get('status')
        kyc = request.form.get('kyc')

        file = request.files.get('profile')

        if file and file.filename != "":
            safe_name = secure_filename(file.filename)
            # avoid collisions
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            final_name = f"{stamp}_{safe_name}" if safe_name else ""
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], final_name)
            file.save(filepath)
            profile = final_name
        else:
            profile = ""

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO employees (
            emp_id, name, dob, gender, job_title, department,
            joining_date, employment_type, manager, location,
            email, phone, emergency, status, kyc, profile
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            emp_id, name, dob, gender, job, dept,
            join, emp_type, manager, location,
            email, phone, emergency, status, kyc, profile
        ))

        conn.commit()
        conn.close()

        return redirect("/employees")

    return render_template("add_employee.html")


# 📋 EMPLOYEES
@app.route("/employees")
@login_required
def employees():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template("employees.html", employees=data)


# 🔍 PROFILE
@app.route("/employee/<int:id>")
@login_required
def employee_profile(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees WHERE id=?", (id,))
    emp = cursor.fetchone()
    if not emp:
        conn.close()
        return render_template("employee_profile.html", emp=None, attendance=[], payroll=[])

    # recent records
    cursor.execute("SELECT * FROM attendance WHERE emp_id=? ORDER BY id DESC LIMIT 10", (emp[1],))
    att = cursor.fetchall()
    cursor.execute("SELECT * FROM payroll WHERE emp_id=? ORDER BY id DESC LIMIT 10", (emp[1],))
    pay = cursor.fetchall()

    conn.close()

    return render_template("employee_profile.html", emp=emp, attendance=att, payroll=pay)


# ❌ DELETE
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT profile FROM employees WHERE id=?", (id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], row[0]))
        except OSError:
            pass

    cursor.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/employees")


# 🔥 ATTENDANCE
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        att_date = request.form.get("date") or date.today().isoformat()
        emp_id = (request.form.get("emp_id") or "").strip()
        name = (request.form.get("name") or "").strip()
        status = (request.form.get("status") or "Present").strip()

        if not emp_id or not name:
            # Do not insert invalid row
            cursor.execute("SELECT emp_id, name FROM employees ORDER BY name")
            employees = cursor.fetchall()
            cursor.execute("SELECT * FROM attendance ORDER BY id DESC")
            data = cursor.fetchall()
            # stats (today)
            today = date.today().isoformat()
            cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'", (today,))
            p = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'", (today,))
            a = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Leave'", (today,))
            l = cursor.fetchone()[0]
            conn.close()
            return render_template(
                "attendance.html",
                data=data,
                employees=employees,
                present_today=p,
                absent_today=a,
                leave_today=l,
                error="Emp ID aur Name required hai.",
            )

        cursor.execute("""
        INSERT INTO attendance (emp_id, name, date, status)
        VALUES (?, ?, ?, ?)
        """, (
            emp_id,
            name,
            att_date,
            status
        ))
        conn.commit()

    cursor.execute("SELECT * FROM attendance ORDER BY id DESC")
    data = cursor.fetchall()

    cursor.execute("SELECT emp_id, name FROM employees ORDER BY name")
    employees = cursor.fetchall()

    # stats (today)
    today = date.today().isoformat()
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'", (today,))
    p = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'", (today,))
    a = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='Leave'", (today,))
    l = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "attendance.html",
        data=data,
        employees=employees,
        present_today=p,
        absent_today=a,
        leave_today=l,
    )


# 🔥 PAYROLL
@app.route("/payroll", methods=["GET", "POST"])
@login_required
def payroll():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        emp_id = (request.form.get("emp_id") or "").strip()
        name = (request.form.get("name") or "").strip()
        basic_raw = (request.form.get("basic") or "").strip()
        bonus_raw = (request.form.get("bonus") or "").strip()
        deduction_raw = (request.form.get("deduction") or "").strip()

        # Validation: avoid "blank submit creates 0 salary" problem
        if not emp_id or not name:
            error = "Emp ID aur Name required hai."
        elif basic_raw == "" and bonus_raw == "" and deduction_raw == "":
            error = "Salary values blank nahi ho sakte. Basic/Bonus/Deduction me se kuch toh dalo."
        else:
            error = None

        def to_float(v):
            try:
                return float(v) if v != "" else 0.0
            except ValueError:
                return None

        basic = to_float(basic_raw)
        bonus = to_float(bonus_raw)
        deduction = to_float(deduction_raw)

        if error is None and (basic is None or bonus is None or deduction is None):
            error = "Basic/Bonus/Deduction me sirf number allowed hai."

        if error is None:
            total = (basic or 0) + (bonus or 0) - (deduction or 0)
            cursor.execute("""
            INSERT INTO payroll (emp_id, name, basic, bonus, deduction, total, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                emp_id,
                name,
                basic or 0, bonus or 0, deduction or 0, total,
                date.today().isoformat()
            ))
            conn.commit()
        else:
            cursor.execute("SELECT emp_id, name FROM employees ORDER BY name")
            employees = cursor.fetchall()
            cursor.execute("SELECT SUM(total) FROM payroll")
            total_payout = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM payroll")
            total_records = cursor.fetchone()[0]
            cursor.execute("SELECT * FROM payroll ORDER BY id DESC")
            data = cursor.fetchall()
            conn.close()
            return render_template(
                "payroll.html",
                data=data,
                total_payout=total_payout,
                total_records=total_records,
                employees=employees,
                error=error,
            )

    cursor.execute("SELECT SUM(total) FROM payroll")
    total_payout = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM payroll")
    total_records = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM payroll ORDER BY id DESC")
    data = cursor.fetchall()

    cursor.execute("SELECT emp_id, name FROM employees ORDER BY name")
    employees = cursor.fetchall()

    conn.close()

    return render_template("payroll.html",
        data=data,
        total_payout=total_payout,
        total_records=total_records,
        employees=employees,
    )


# 🔥 REPORTS
@app.route("/reports")
@login_required
def reports():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_emp = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM payroll")
    total_salary = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_att = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM payroll ORDER BY id DESC LIMIT 5")
    payroll_data = cursor.fetchall()

    # Monthly payroll trend (real chart)
    cursor.execute(
        "SELECT substr(date,1,7) as ym, SUM(total) FROM payroll "
        "GROUP BY substr(date,1,7) ORDER BY ym"
    )
    monthly_pay = cursor.fetchall()

    # Attendance status split (real chart)
    cursor.execute("SELECT status, COUNT(*) FROM attendance GROUP BY status")
    att_split = cursor.fetchall()

    conn.close()

    return render_template("reports.html",
        total_emp=total_emp,
        total_salary=total_salary,
        total_att=total_att,
        payroll_data=payroll_data,
        monthly_pay=monthly_pay,
        att_split=att_split,
    )


# 🔥 ANALYTICS (UNCHANGED)
@app.route("/analytics")
@login_required
def analytics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_emp = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM payroll")
    total_salary = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_att = cursor.fetchone()[0]

    cursor.execute("SELECT department, COUNT(*) FROM employees GROUP BY department")
    dept_data = cursor.fetchall()

    cursor.execute("SELECT gender, COUNT(*) FROM employees GROUP BY gender")
    gender_data = cursor.fetchall()

    cursor.execute("SELECT status, COUNT(*) FROM attendance GROUP BY status")
    att_status = cursor.fetchall()

    cursor.execute("SELECT name, total FROM payroll ORDER BY total DESC LIMIT 5")
    top_salary = cursor.fetchall()

    cursor.execute("SELECT substr(date,1,7), SUM(total) FROM payroll GROUP BY substr(date,1,7)")
    monthly = cursor.fetchall()

    conn.close()

    return render_template("analytics.html",
        total_emp=total_emp,
        total_salary=total_salary,
        total_att=total_att,
        dept_data=dept_data,
        gender_data=gender_data,
        att_status=att_status,
        top_salary=top_salary,
        monthly=monthly
    )

@app.route("/notifications")
@login_required
def notifications():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM notifications ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template("notifications.html", data=data)


@app.route("/add_notification", methods=["GET", "POST"])
@login_required
def add_notification():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        message = (request.form.get("message") or "").strip()
        if title and message:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notifications (title, message, status, date) VALUES (?, ?, 'unread', ?)",
                (title, message, date.today().isoformat()),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("notifications"))
        return render_template("add_notification.html", error="Title aur message required hai.")

    return render_template("add_notification.html")


@app.route("/read/<int:notif_id>")
@login_required
def read_notification(notif_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET status='read' WHERE id=?", (notif_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("notifications"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        theme = (request.form.get("theme") or "Purple").strip()
        new_password = (request.form.get("password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM admin WHERE username=?", (session["admin"],))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return redirect(url_for("logout"))

        if new_password:
            if new_password != confirm_password:
                conn.close()
                return render_template("settings.html", message=None, error="Password match nahi ho raha.")
            cursor.execute(
                "UPDATE admin SET password=? WHERE id=?",
                (generate_password_hash(new_password), row[0]),
            )

        cursor.execute(
            "UPDATE admin SET name=?, email=?, theme=? WHERE id=?",
            (name or None, email or None, theme, row[0]),
        )
        conn.commit()
        conn.close()

        session["theme"] = theme
        return render_template("settings.html", message="Settings save ho gaye ✅")

    return render_template("settings.html")


if __name__ == "__main__":
    # Preview-friendly defaults
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
