# Edumetric Backend

FastAPI backend for the PDP University grant and performance monitoring system.

The backend runs with a self-contained SQLite database by default, exposes the API under `/api`, and implements the core workflows for authentication, student scoring, attendance, grades, achievements, feedback, tutor ratings, penalties, recovery tasks, employment verification, admin dashboards, and public leaderboard access.

## Stack

- Python 3.14+
- FastAPI
- SQLAlchemy 2.x async ORM
- SQLite by default via `aiosqlite`
- JWT-style bearer tokens implemented in `app/core/security.py`
- Pydantic and Pydantic Settings
- Alembic is still available for manual schema migrations if needed

## Project Layout

```text
app/
  main.py                FastAPI entrypoint
  core/                  Config, security, RBAC, error handling
  db/                    Async engine, Base metadata, seed module
  models/                SQLAlchemy models and enums
  routers/               Auth + Edumetric API routers
  services/              Auth, audit, notification, score engine
scripts/
  seed_demo_data.py      CLI wrapper for the demo seed
tests/
  test_main.py           Smoke tests
```

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The backend works out of the box with the SQLite default in `.env.example`:

```env
DATABASE_URL_OVERRIDE=sqlite+aiosqlite:///./data/edumetrik.db
SECRET_KEY=change-me-in-production
UPLOAD_DIR=./uploads
```

## Run

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## Seed Demo Data

The demo seed resets the database and populates a complete showcase dataset:

```bash
python -m app.db.seed
```

Demo credentials:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@pdp.uz` | `DemoPass123!` |
| Mentor 1 | `mentor1@pdp.uz` | `DemoPass123!` |
| Mentor 2 | `mentor2@pdp.uz` | `DemoPass123!` |
| Mentor 3 | `mentor3@pdp.uz` | `DemoPass123!` |
| Student 01-20 | `student01@pdp.uz` ... `student20@pdp.uz` | `DemoPass123!` |
| Parent 01-20 | `parent01@pdp.uz` ... `parent20@pdp.uz` | `DemoPass123!` |

## API Summary

Base URL: `/api`

### Auth

- `POST /api/auth/login`
- `GET /api/auth/me`
- `PUT /api/auth/me`
- `POST /api/auth/change-password`

Login uses the stored username field as the credential identifier. Public self-registration is disabled; admins provision student accounts from `/api/admin/users`, and the backend returns the generated username and password in the response.

### Students and Leaderboard

- `GET /api/students`
- `GET /api/students/leaderboard`
- `GET /api/students/leaderboard/guest`
- `GET /api/students/{student_id}`
- `GET /api/students/{student_id}/score`
- `GET /api/students/{student_id}/score/history`
- `GET /api/students/{student_id}/feed`
- `POST /api/students/{student_id}/recalculate`

### Attendance

- `POST /api/attendance`
- `POST /api/attendance/bulk`
- `GET /api/attendance/{student_id}`
- `GET /api/attendance/course/{course_id}`
- `PUT /api/attendance/{attendance_id}`
- `GET /api/attendance/stats/{student_id}`

### Grades

- `POST /api/grades`
- `GET /api/grades/{student_id}`
- `PUT /api/grades/{grade_id}`
- `DELETE /api/grades/{grade_id}`
- `GET /api/grades/stats/{student_id}`

### Achievements

- `POST /api/achievements`
- `GET /api/achievements`
- `GET /api/achievements/my`
- `GET /api/achievements/{achievement_id}`
- `PUT /api/achievements/{achievement_id}/approve`
- `PUT /api/achievements/{achievement_id}/reject`
- `DELETE /api/achievements/{achievement_id}`

### Feedback and Tutor Ratings

- `POST /api/feedback`
- `GET /api/feedback/student/{student_id}`
- `GET /api/feedback/my-given`
- `PUT /api/feedback/{feedback_id}`
- `DELETE /api/feedback/{feedback_id}`
- `POST /api/tutor-ratings`
- `GET /api/tutor-ratings/{student_id}`

### Penalties, Recovery, Employment

- `POST /api/penalties`
- `GET /api/penalties/{student_id}`
- `POST /api/penalties/recovery`
- `PUT /api/penalties/recovery/{task_id}/complete`
- `PUT /api/penalties/recovery/{task_id}/verify`
- `POST /api/employment`
- `GET /api/employment/my`
- `GET /api/employment`
- `PUT /api/employment/{employment_id}/verify`

### Admin

- `GET /api/admin/dashboard`
- `GET /api/admin/audit-log`
- `POST /api/admin/users`
- `PUT /api/admin/users/{user_id}/toggle`
- `GET /api/admin/reports/grant`
- `POST /api/admin/recalculate-all`
- `POST /api/admin/notifications/send`

### Utility Routes

- `GET /api/users`
- `GET /api/users/{user_id}`
- `PUT /api/users/{user_id}`
- `DELETE /api/users/{user_id}`
- `GET /api/groups`
- `POST /api/groups`
- `GET /api/academic-years`
- `POST /api/academic-years`
- `PUT /api/academic-years/{academic_year_id}`
- `GET /api/semesters`
- `POST /api/semesters`
- `GET /api/courses`
- `POST /api/courses`

## Scoring Model

- Academic: 40
- Attendance: 20
- Practical skills: 15
- Activity / certificates: 10
- Tutor rating: 5
- Discipline: 10
- Penalty: down to -20
- Recovery: up to +10
- Employment bonus: up to +10

Grant eligibility:

```text
final_score >= 80 AND academic_percentage >= 80
```

## Testing

```bash
pytest -q
```

## Notes

- The backend creates SQLite tables on startup.
- Uploads are stored in `./uploads`.
- `app/models` is the single source of truth for ORM metadata.
- `python -m app.db.seed` is the canonical demo seed command.
