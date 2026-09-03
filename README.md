# Hostel Service & Complaint Management System

A Flask-based complaint system designed for a hostel. Students can register, log in, submit complaints with room number, and track status. The administrator can view every complaint and update its status/notes.

## Main features
- Student registration and login
- Room number with every complaint
- Complaint category, subject, description and priority
- Student complaint history and status tracking
- Admin dashboard with Total / Pending / In Progress / Resolved counts
- Admin notes and status updates
- User management
- Password hashing
- SQLite for local use
- PostgreSQL support for online deployment
- Production start command using Gunicorn
- `/health` health-check endpoint

## Run locally
```bash
pip install -r requirements.txt
python app.py
```

The browser opens automatically at:
http://127.0.0.1:5000

## Default admin
- Email: `admin@gmail.com`
- Password: `admin123`

For real use, set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `SECRET_KEY` as environment variables.

## Online deployment
This project is prepared for Render. Connect the project repository, create a Python Web Service, use:

Build Command:
```text
pip install -r requirements.txt
```

Start Command:
```text
gunicorn app:app
```

For real hostel data, use a PostgreSQL database through the `DATABASE_URL` environment variable. Do not rely on local SQLite for persistent cloud data on an ephemeral filesystem.
