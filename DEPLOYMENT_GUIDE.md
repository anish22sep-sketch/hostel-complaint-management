# Online Hostel Deployment - Beginner Guide

## What you will get
A public web address such as:
`https://hostel-complaint-system.onrender.com`

Students can open the address on their phone and submit complaints. You can log in with the admin account and see the complaints in the Admin Dashboard.

## Step 1: Create a GitHub repository
1. Create a GitHub account if you do not already have one.
2. Create a new repository, for example `hostel-complaint-system`.
3. Upload all files from this project folder to the repository.
4. Make sure `app.py`, `requirements.txt`, `templates`, and `static` are in the repository root.

## Step 2: Create a Render Web Service
1. Sign in to Render.
2. Choose **New -> Web Service**.
3. Connect your GitHub repository.
4. Runtime: **Python 3**.
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `gunicorn app:app`
7. Choose a plan suitable for your use.

## Step 3: Add environment variables
Add these in the Render Environment settings:
- `SECRET_KEY` = a long random secret
- `ADMIN_EMAIL` = your admin email
- `ADMIN_PASSWORD` = a strong admin password
- `DATABASE_URL` = your PostgreSQL connection string

## Step 4: Create PostgreSQL
Create a Render Postgres database and connect its internal database URL to the web service as `DATABASE_URL`.

Important: Render's free web service filesystem is ephemeral, so local SQLite data can disappear after restarts/redeploys. Render documents PostgreSQL as the persistent relational-data option. Its free Postgres plan currently expires after 30 days, so use a paid database if you need long-term hostel records.

## Step 5: Open the live URL
After deployment finishes, Render gives you an `onrender.com` URL. Open it on your phone.

## Student flow
Register -> Login -> New Complaint -> Enter Room Number -> Submit -> Track Status

## Admin flow
Login -> Admin Dashboard -> See complaint -> Change Pending/In Progress/Resolved -> Add note
