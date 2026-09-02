import os
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, DateTime, ForeignKey, select, func, update, delete
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite:"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("email", Text, nullable=False, unique=True),
    Column("phone", Text),
    Column("password", Text, nullable=False),
    Column("role", Text, nullable=False, default="user"),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
)

complaints = Table(
    "complaints", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("category", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("room_no", Text),
    Column("priority", Text, nullable=False, default="Medium"),
    Column("status", Text, nullable=False, default="Pending"),
    Column("admin_note", Text),
    Column("created_at", DateTime, server_default=func.current_timestamp()),
    Column("updated_at", DateTime, server_default=func.current_timestamp()),
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key-before-production")


def init_db():
    metadata.create_all(engine)
    # Small migration for older local copies of this project.
    with engine.begin() as conn:
        try:
            conn.execute(__import__('sqlalchemy').text("ALTER TABLE complaints ADD COLUMN room_no TEXT"))
        except Exception:
            pass

        admin_email = os.getenv("ADMIN_EMAIL", "admin@gmail.com").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        existing = conn.execute(select(users.c.id).where(users.c.email == admin_email)).first()
        if not existing:
            conn.execute(users.insert().values(
                name="Administrator",
                email=admin_email,
                phone="",
                password=generate_password_hash(admin_password),
                role="admin",
            ))


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return render_template("register.html")

        try:
            with engine.begin() as conn:
                conn.execute(users.insert().values(
                    name=name, email=email, phone=phone,
                    password=generate_password_hash(password), role="user"
                ))
        except IntegrityError:
            flash("This email is already registered.", "danger")
            return render_template("register.html")

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with engine.connect() as conn:
            user = conn.execute(select(users).where(users.c.email == email)).mappings().first()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["email"] = user["email"]
            return redirect(url_for("admin" if user["role"] == "admin" else "dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin"))

    with engine.connect() as conn:
        rows = conn.execute(
            select(complaints).where(complaints.c.user_id == session["user_id"]).order_by(complaints.c.id.desc())
        ).mappings().all()
    return render_template("dashboard.html", complaints=rows)


@app.route("/complaint", methods=["GET", "POST"])
@login_required
def complaint():
    if session.get("role") == "admin":
        return redirect(url_for("admin"))

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "Medium")
        room_no = request.form.get("room_no", "").strip()

        if not category or not subject or not description:
            flash("Please fill all complaint fields.", "danger")
            return render_template("complaint.html")
        if priority not in ("Low", "Medium", "High"):
            priority = "Medium"

        with engine.begin() as conn:
            conn.execute(complaints.insert().values(
                user_id=session["user_id"], category=category, subject=subject,
                description=description, priority=priority, status="Pending", room_no=room_no
            ))

        flash("Complaint submitted successfully. The administrator can now see it.", "success")
        return redirect(url_for("dashboard"))

    return render_template("complaint.html")


@app.route("/delete_complaint/<int:id>", methods=["POST"])
@login_required
def delete_complaint(id):
    with engine.begin() as conn:
        result = conn.execute(delete(complaints).where(
            complaints.c.id == id, complaints.c.user_id == session["user_id"]
        ))
    flash("Complaint deleted." if result.rowcount else "Complaint not found.", "success" if result.rowcount else "danger")
    return redirect(url_for("dashboard"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not name:
            flash("Name cannot be empty.", "danger")
        else:
            with engine.begin() as conn:
                conn.execute(update(users).where(users.c.id == session["user_id"]).values(name=name, phone=phone))
            session["name"] = name
            flash("Profile updated successfully.", "success")

    with engine.connect() as conn:
        user = conn.execute(
            select(users.c.id, users.c.name, users.c.email, users.c.phone, users.c.role, users.c.created_at)
            .where(users.c.id == session["user_id"])
        ).mappings().first()
    return render_template("profile.html", user=user)


@app.route("/admin")
@admin_required
def admin():
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                complaints,
                users.c.name.label("name"),
                users.c.email.label("email"),
                users.c.phone.label("phone")
            ).join(users, complaints.c.user_id == users.c.id).order_by(complaints.c.id.desc())
        ).mappings().all()

        total = conn.execute(select(func.count()).select_from(complaints)).scalar_one()
        pending = conn.execute(select(func.count()).select_from(complaints).where(complaints.c.status == "Pending")).scalar_one()
        progress = conn.execute(select(func.count()).select_from(complaints).where(complaints.c.status == "In Progress")).scalar_one()
        resolved = conn.execute(select(func.count()).select_from(complaints).where(complaints.c.status == "Resolved")).scalar_one()

        user_rows = conn.execute(
            select(users.c.id, users.c.name, users.c.email, users.c.phone, users.c.created_at)
            .where(users.c.role == "user").order_by(users.c.id.desc())
        ).mappings().all()

    return render_template("admin.html", complaints=rows, total=total, pending=pending,
                           progress=progress, resolved=resolved, users=user_rows)


@app.route("/update_status/<int:id>", methods=["POST"])
@admin_required
def update_status(id):
    status = request.form.get("status", "Pending")
    note = request.form.get("admin_note", "").strip()
    if status not in ("Pending", "In Progress", "Resolved"):
        status = "Pending"

    with engine.begin() as conn:
        conn.execute(update(complaints).where(complaints.c.id == id).values(
            status=status, admin_note=note, updated_at=func.current_timestamp()
        ))
    flash("Complaint updated successfully.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:id>", methods=["POST"])
@admin_required
def admin_delete(id):
    with engine.begin() as conn:
        conn.execute(delete(complaints).where(complaints.c.id == id))
    flash("Complaint deleted.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users")
@admin_required
def admin_users():
    with engine.connect() as conn:
        rows = conn.execute(
            select(users.c.id, users.c.name, users.c.email, users.c.phone, users.c.created_at)
            .where(users.c.role == "user").order_by(users.c.id.desc())
        ).mappings().all()
    return render_template("users.html", users=rows)


@app.get("/health")
def health():
    return {"status": "ok"}, 200


init_db()

if __name__ == "__main__":
    import webbrowser
    from threading import Timer
    port = int(os.getenv("PORT", "5000"))
    if not os.getenv("RENDER"):
        Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False)
