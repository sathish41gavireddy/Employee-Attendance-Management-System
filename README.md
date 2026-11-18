# Employee Attendance System

A simple web application to manage employees and track their daily attendance.
Built with **Python (Flask)**, **SQLite**, and a plain **HTML/CSS/JavaScript** frontend.

---

## Features

### Core
- Add employee records (ID, name, department)
- Mark employees as **Present** or **Absent**
- View daily attendance for any date
- Calculate attendance percentage per employee
- Search employees by name or ID
- Filter attendance by date (single day or date range)

### Bonus
- **Duplicate prevention**: an employee cannot be marked twice on the same day
- **Attendance reports** with CSV download
- **Low attendance highlight**: employees below 75% are shown in red

---

## Tech Stack

| Layer     | Technology                         |
|-----------|------------------------------------|
| Backend   | Python 3, Flask (REST API)         |
| Database  | SQLite (file: `attendance.db`)     |
| Frontend  | HTML, CSS, vanilla JavaScript      |

---

## Project Structure

```
Employee_Attendance_System/
├── app.py              # Flask server, API routes, database logic
├── requirements.txt    # Python dependencies (Flask)
├── README.md           # This file
├── attendance.db       # SQLite database (created automatically)
└── static/
    └── index.html      # User interface
```

---

## How to Run (VS Code)

1. Open the project folder in VS Code (File > Open Folder).
2. Open the terminal (Ctrl + `) and run:

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux
pip install -r requirements.txt
python app.py
```

3. Open **http://127.0.0.1:5000** in your browser.

The database file is created automatically on first run. Data is saved
permanently, so it is still there after you restart the server.

To stop the server, press **Ctrl + C** in the terminal.

---

## How to Use

1. **Employees tab**: enter ID, name and department, then click *Add Employee*.
   Use the search box to find employees by name or ID.
2. **Daily Attendance tab**: pick a date, then click *Present* or *Absent*
   next to each employee. Unmarked employees show "Not marked".
3. **Report tab**: see total days, present days, absent days and attendance %.
   Filter by date range, search, or click *Download CSV*.
   Rows below 75% are highlighted in red.

---

## Database Design

**employees**

| Column      | Type    | Notes                  |
|-------------|---------|------------------------|
| id          | INTEGER | Primary key            |
| employee_id | TEXT    | Unique, required       |
| name        | TEXT    | Required               |
| department  | TEXT    | Optional               |

**attendance**

| Column      | Type    | Notes                                    |
|-------------|---------|------------------------------------------|
| id          | INTEGER | Primary key                              |
| employee_id | TEXT    | Foreign key to employees (cascade delete)|
| date        | TEXT    | Format YYYY-MM-DD                        |
| status      | TEXT    | Only `Present` or `Absent`               |

A `UNIQUE (employee_id, date)` constraint guarantees no duplicate attendance.

**Attendance % formula:** `present days / total recorded days x 100`

---

## API Reference

| Method | Endpoint                     | Description                                  |
|--------|------------------------------|----------------------------------------------|
| GET    | `/api/employees?q=`          | List or search employees                     |
| POST   | `/api/employees`             | Add an employee                              |
| DELETE | `/api/employees/<id>`        | Delete an employee and their records         |
| GET    | `/api/attendance?date=&q=`   | Attendance for a date (all employees)        |
| POST   | `/api/attendance`            | Mark attendance (409 if already marked)      |
| PUT    | `/api/attendance`            | Correct an existing attendance record        |
| GET    | `/api/report?start=&end=&q=` | Attendance report with percentages           |
| GET    | `/api/report.csv`            | Download the report as CSV                   |

Example request body for `POST /api/attendance`:

```json
{ "employee_id": "E1", "date": "2026-11-18", "status": "Present" }
```

---

## Error Handling

| Code | Meaning                                                     |
|------|-------------------------------------------------------------|
| 400  | Missing or invalid input (empty fields, bad date or status) |
| 404  | Employee or record not found                                |
| 409  | Duplicate employee ID or duplicate attendance entry         |
| 500  | Unexpected server error                                     |

All errors return JSON like `{"error": "message"}`, and the UI shows them
as a pop-up message.

---

## Troubleshooting

- **`TemplateNotFound: index.html`**: `index.html` must be inside a folder
  named `static` (not `templates`), next to `app.py`.
- **Old error still shows after fixing**: another server may still be running
  on port 5000. Close all terminals, or run on another port:
  `python -c "import app; app.init_db(); app.app.run(port=5001, debug=True)"`
  and open http://127.0.0.1:5001.
- **`python` not recognized**: try `py app.py`.
- **`No such file ... app.pypython`**: you pasted two commands together.
  Type `python app.py` on its own.
