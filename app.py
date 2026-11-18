import csv
import io
import sqlite3
from datetime import datetime

from flask import Flask, Response, g, jsonify, request

app = Flask(__name__, static_folder="static", static_url_path="")
DB_PATH = "attendance.db"
THRESHOLD = 75.0


# ---------- Database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                department TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('Present','Absent')),
                UNIQUE (employee_id, date),
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
            );
            """
        )


# ---------- Helpers ----------
def error(message, code=400):
    return jsonify({"error": message}), code


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def like(q):
    return f"%{(q or '').strip()}%"


@app.errorhandler(404)
def not_found(_):
    return error("Not found", 404)


@app.errorhandler(500)
def server_error(_):
    return error("Internal server error", 500)


@app.route("/")
def index():
    return app.send_static_file("index.html")


# ---------- Employees ----------
@app.get("/api/employees")
def list_employees():
    q = like(request.args.get("q"))
    rows = get_db().execute(
        "SELECT employee_id, name, department FROM employees "
        "WHERE name LIKE ? OR employee_id LIKE ? ORDER BY name",
        (q, q),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/employees")
def add_employee():
    data = request.get_json(silent=True) or {}
    emp_id = str(data.get("employee_id", "")).strip()
    name = str(data.get("name", "")).strip()
    dept = str(data.get("department", "")).strip()
    if not emp_id or not name:
        return error("Employee ID and name are required.")
    try:
        db = get_db()
        db.execute(
            "INSERT INTO employees (employee_id, name, department) VALUES (?,?,?)",
            (emp_id, name, dept),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error(f"Employee ID '{emp_id}' already exists.", 409)
    return jsonify({"employee_id": emp_id, "name": name, "department": dept}), 201


@app.delete("/api/employees/<emp_id>")
def delete_employee(emp_id):
    db = get_db()
    cur = db.execute("DELETE FROM employees WHERE employee_id = ?", (emp_id,))
    db.commit()
    if cur.rowcount == 0:
        return error("Employee not found.", 404)
    return jsonify({"deleted": emp_id})


# ---------- Attendance ----------
@app.get("/api/attendance")
def daily_attendance():
    day = request.args.get("date", "")
    if not valid_date(day):
        return error("A valid date (YYYY-MM-DD) is required.")
    q = like(request.args.get("q"))
    rows = get_db().execute(
        "SELECT e.employee_id, e.name, e.department, a.status "
        "FROM employees e LEFT JOIN attendance a "
        "ON a.employee_id = e.employee_id AND a.date = ? "
        "WHERE e.name LIKE ? OR e.employee_id LIKE ? ORDER BY e.name",
        (day, q, q),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


def _save_attendance(update):
    data = request.get_json(silent=True) or {}
    emp_id = str(data.get("employee_id", "")).strip()
    day = data.get("date", "")
    status = data.get("status", "")
    if not emp_id or not valid_date(day):
        return error("Employee ID and a valid date (YYYY-MM-DD) are required.")
    if status not in ("Present", "Absent"):
        return error("Status must be 'Present' or 'Absent'.")
    db = get_db()
    if not db.execute("SELECT 1 FROM employees WHERE employee_id=?", (emp_id,)).fetchone():
        return error("Employee not found.", 404)
    if update:
        cur = db.execute(
            "UPDATE attendance SET status=? WHERE employee_id=? AND date=?",
            (status, emp_id, day),
        )
        db.commit()
        if cur.rowcount == 0:
            return error("No attendance record to update.", 404)
        return jsonify({"employee_id": emp_id, "date": day, "status": status})
    try:
        db.execute(
            "INSERT INTO attendance (employee_id, date, status) VALUES (?,?,?)",
            (emp_id, day, status),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error(f"Attendance for {emp_id} on {day} is already marked.", 409)
    return jsonify({"employee_id": emp_id, "date": day, "status": status}), 201


@app.post("/api/attendance")
def mark_attendance():
    return _save_attendance(update=False)


@app.put("/api/attendance")
def correct_attendance():
    return _save_attendance(update=True)


# ---------- Reports ----------
def build_report(q, start, end):
    rows = get_db().execute(
        "SELECT e.employee_id, e.name, e.department, COUNT(a.id) AS total, "
        "COALESCE(SUM(a.status='Present'),0) AS present "
        "FROM employees e LEFT JOIN attendance a "
        "ON a.employee_id = e.employee_id AND a.date >= ? AND a.date <= ? "
        "WHERE e.name LIKE ? OR e.employee_id LIKE ? "
        "GROUP BY e.employee_id ORDER BY e.name",
        (start or "0000-01-01", end or "9999-12-31", q, q),
    ).fetchall()
    out = []
    for r in rows:
        total, present = r["total"], r["present"]
        pct = round(present * 100 / total, 2) if total else None
        out.append({
            "employee_id": r["employee_id"], "name": r["name"],
            "department": r["department"], "total_days": total,
            "present_days": present, "absent_days": total - present,
            "percentage": pct, "low": pct is not None and pct < THRESHOLD,
        })
    return out


def report_args():
    start, end = request.args.get("start") or None, request.args.get("end") or None
    for d in (start, end):
        if d and not valid_date(d):
            return None, None, error("Dates must be in YYYY-MM-DD format.")
    return start, end, None


@app.get("/api/report")
def report():
    start, end, err = report_args()
    if err:
        return err
    return jsonify(build_report(like(request.args.get("q")), start, end))


@app.get("/api/report.csv")
def report_csv():
    start, end, err = report_args()
    if err:
        return err
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Employee ID", "Name", "Department", "Total Days", "Present", "Absent", "Attendance %", "Below 75%"])
    for r in build_report(like(request.args.get("q")), start, end):
        w.writerow([r["employee_id"], r["name"], r["department"], r["total_days"],
                    r["present_days"], r["absent_days"],
                    "" if r["percentage"] is None else r["percentage"],
                    "Yes" if r["low"] else "No"])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
