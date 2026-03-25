from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def months_to_days(months: int) -> int:
    return months * 30


def next_due_from(last_regular: date, interval_months: int) -> date:
    return last_regular.fromordinal(last_regular.toordinal() + months_to_days(interval_months))


def init_db() -> None:
    db = get_db()
    schema = BASE_DIR / "schema.sql"
    with closing(schema.open("r", encoding="utf-8")) as f:
        db.executescript(f.read())

    admin = db.execute("SELECT id FROM user WHERE email = ?", ("admin@example.com",)).fetchone()
    if admin is None:
        db.execute(
            "INSERT INTO user (name, email, password_hash, role, active) VALUES (?, ?, ?, ?, 1)",
            (
                "Admin",
                "admin@example.com",
                generate_password_hash("admin123"),
                "admin",
            ),
        )

    demo_customer = db.execute("SELECT id FROM customer WHERE customer_number = ?", ("K-1000",)).fetchone()
    if demo_customer is None:
        db.execute(
            "INSERT INTO customer (customer_number, name, address, phone, email, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "K-1000",
                "Musterkunde GmbH",
                "Beispielweg 1, 12345 Musterstadt",
                "+49 123 456789",
                "info@musterkunde.de",
                "Demo-Datensatz",
            ),
        )
        customer_id = db.execute("SELECT id FROM customer WHERE customer_number = ?", ("K-1000",)).fetchone()["id"]
        today = date.today()
        last = today.fromordinal(today.toordinal() - 120)
        next_due = next_due_from(last, 3)
        db.execute(
            """
            INSERT INTO asset (
                customer_id, asset_number, location, asset_type, manufacturer, model,
                commissioning_date, maintenance_interval_months, last_regular_maintenance_at,
                next_maintenance_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                "A-1000",
                "Hauptstraße 1",
                "Kleinkläranlage",
                "AquaTech",
                "AT-Plus",
                "2020-06-01",
                3,
                last.isoformat(),
                next_due.isoformat(),
                "aktiv",
            ),
        )

    db.commit()


def ensure_today_maintenance_jobs() -> None:
    db = get_db()
    today = date.today().isoformat()
    assets = db.execute(
        """
        SELECT a.id, a.customer_id, a.next_maintenance_at
        FROM asset a
        WHERE a.status = 'aktiv' AND a.next_maintenance_at IS NOT NULL AND a.next_maintenance_at <= ?
        """,
        (today,),
    ).fetchall()

    for asset in assets:
        existing = db.execute(
            "SELECT id FROM planned_maintenance WHERE asset_id = ? AND due_date = ? AND status IN ('offen', 'begonnen')",
            (asset["id"], asset["next_maintenance_at"]),
        ).fetchone()
        if existing is None:
            db.execute(
                """
                INSERT INTO planned_maintenance (asset_id, customer_id, due_date, status, source, created_at)
                VALUES (?, ?, ?, 'offen', 'automatisch', ?)
                """,
                (asset["id"], asset["customer_id"], asset["next_maintenance_at"], datetime.utcnow().isoformat()),
            )

    db.execute(
        "UPDATE planned_maintenance SET status = 'ueberfaellig' WHERE status = 'offen' AND due_date < ?",
        (today,),
    )
    db.commit()


def require_login() -> bool:
    if "user_id" not in session:
        flash("Bitte zuerst anmelden.")
        return False
    return True


@app.route("/")
def index() -> Any:
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/setup")
def setup() -> Any:
    init_db()
    return "Setup erfolgreich. Admin: admin@example.com / admin123"


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM user WHERE email = ? AND active = 1", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Login fehlgeschlagen.")
    return render_template("login.html")


@app.route("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard() -> Any:
    if not require_login():
        return redirect(url_for("login"))

    ensure_today_maintenance_jobs()
    db = get_db()
    today = date.today().isoformat()

    stats = {
        "due_today": db.execute("SELECT COUNT(*) c FROM planned_maintenance WHERE due_date = ?", (today,)).fetchone()["c"],
        "overdue": db.execute(
            "SELECT COUNT(*) c FROM planned_maintenance WHERE due_date < ? AND status IN ('offen', 'ueberfaellig')",
            (today,),
        ).fetchone()["c"],
        "completed_today": db.execute(
            "SELECT COUNT(*) c FROM maintenance_protocol WHERE date(protocol_date) = ?", (today,)
        ).fetchone()["c"],
        "due_week": db.execute(
            "SELECT COUNT(*) c FROM planned_maintenance WHERE due_date BETWEEN ? AND date(?, '+7 day')",
            (today, today),
        ).fetchone()["c"],
    }

    rows = db.execute(
        """
        SELECT pm.id, pm.due_date, pm.status, c.name AS customer_name,
               a.asset_number, a.location
        FROM planned_maintenance pm
        JOIN customer c ON c.id = pm.customer_id
        JOIN asset a ON a.id = pm.asset_id
        WHERE pm.due_date <= date(?, '+7 day')
        ORDER BY pm.due_date ASC
        """,
        (today,),
    ).fetchall()

    return render_template("dashboard.html", stats=stats, rows=rows)


@app.route("/customers", methods=["GET", "POST"])
def customers() -> Any:
    if not require_login():
        return redirect(url_for("login"))

    db = get_db()
    if request.method == "POST":
        db.execute(
            "INSERT INTO customer (customer_number, name, address, phone, email, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                request.form.get("customer_number"),
                request.form.get("name"),
                request.form.get("address"),
                request.form.get("phone"),
                request.form.get("email"),
                request.form.get("notes"),
            ),
        )
        db.commit()
        flash("Kunde angelegt.")
        return redirect(url_for("customers"))

    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            """
            SELECT * FROM customer
            WHERE customer_number LIKE ? OR name LIKE ? OR email LIKE ?
            ORDER BY name ASC
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM customer ORDER BY name ASC").fetchall()

    return render_template("customers.html", rows=rows, q=q)


@app.route("/assets", methods=["GET", "POST"])
def assets() -> Any:
    if not require_login():
        return redirect(url_for("login"))

    db = get_db()
    if request.method == "POST":
        commissioning = parse_date(request.form.get("commissioning_date"))
        interval = int(request.form.get("maintenance_interval_months") or 0)
        last_regular = parse_date(request.form.get("last_regular_maintenance_at"))
        next_due = next_due_from(last_regular, interval) if last_regular and interval > 0 else None

        db.execute(
            """
            INSERT INTO asset (
                customer_id, asset_number, location, asset_type, manufacturer, model,
                commissioning_date, maintenance_interval_months, last_regular_maintenance_at,
                next_maintenance_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.form.get("customer_id"),
                request.form.get("asset_number"),
                request.form.get("location"),
                request.form.get("asset_type"),
                request.form.get("manufacturer"),
                request.form.get("model"),
                commissioning.isoformat() if commissioning else None,
                interval,
                last_regular.isoformat() if last_regular else None,
                next_due.isoformat() if next_due else None,
                request.form.get("status") or "aktiv",
            ),
        )
        db.commit()
        flash("Anlage angelegt.")
        return redirect(url_for("assets"))

    rows = db.execute(
        """
        SELECT a.*, c.name AS customer_name
        FROM asset a
        JOIN customer c ON c.id = a.customer_id
        ORDER BY a.id DESC
        """
    ).fetchall()
    customers_rows = db.execute("SELECT id, name FROM customer ORDER BY name ASC").fetchall()
    return render_template("assets.html", rows=rows, customers=customers_rows)


@app.route("/protocols/new", methods=["GET", "POST"])
def protocol_new() -> Any:
    if not require_login():
        return redirect(url_for("login"))

    db = get_db()
    planned_id = request.args.get("planned_id")
    selected_asset_id = request.args.get("asset_id")

    if request.method == "POST":
        asset_id = int(request.form.get("asset_id"))
        asset = db.execute("SELECT * FROM asset WHERE id = ?", (asset_id,)).fetchone()
        protocol_type = request.form.get("protocol_type")
        regular = 1 if request.form.get("counts_as_regular") == "1" else 0
        protocol_date = request.form.get("protocol_date")

        db.execute(
            """
            INSERT INTO maintenance_protocol (
                asset_id, customer_id, planned_maintenance_id, user_id,
                protocol_date, protocol_type, counts_as_regular,
                checklist, measurements, findings, defects, recommendation,
                completion_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                asset["customer_id"],
                request.form.get("planned_maintenance_id") or None,
                session["user_id"],
                protocol_date,
                protocol_type,
                regular,
                request.form.get("checklist"),
                request.form.get("measurements"),
                request.form.get("findings"),
                request.form.get("defects"),
                request.form.get("recommendation"),
                request.form.get("completion_status"),
                datetime.utcnow().isoformat(),
            ),
        )

        planned_maintenance_id = request.form.get("planned_maintenance_id")
        if planned_maintenance_id:
            db.execute(
                "UPDATE planned_maintenance SET status = 'abgeschlossen', completed_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), planned_maintenance_id),
            )

        if regular:
            dt = parse_date(protocol_date)
            if dt:
                interval = asset["maintenance_interval_months"]
                next_due = next_due_from(dt, interval)
                db.execute(
                    "UPDATE asset SET last_regular_maintenance_at = ?, next_maintenance_at = ? WHERE id = ?",
                    (dt.isoformat(), next_due.isoformat(), asset_id),
                )

        db.commit()
        flash("Wartungsprotokoll gespeichert.")
        return redirect(url_for("protocols"))

    assets_rows = db.execute(
        """
        SELECT a.id, a.asset_number, c.name AS customer_name
        FROM asset a JOIN customer c ON c.id = a.customer_id
        ORDER BY c.name, a.asset_number
        """
    ).fetchall()

    planned = None
    if planned_id:
        planned = db.execute(
            """
            SELECT pm.*, c.name AS customer_name, a.asset_number
            FROM planned_maintenance pm
            JOIN customer c ON c.id = pm.customer_id
            JOIN asset a ON a.id = pm.asset_id
            WHERE pm.id = ?
            """,
            (planned_id,),
        ).fetchone()
        if planned:
            selected_asset_id = str(planned["asset_id"])

    return render_template(
        "protocol_form.html",
        assets=assets_rows,
        planned=planned,
        selected_asset_id=selected_asset_id,
        today=date.today().isoformat(),
    )


@app.route("/protocols")
def protocols() -> Any:
    if not require_login():
        return redirect(url_for("login"))

    rows = get_db().execute(
        """
        SELECT p.id, p.protocol_date, p.protocol_type, p.counts_as_regular,
               c.name AS customer_name, a.asset_number, u.name AS user_name
        FROM maintenance_protocol p
        JOIN customer c ON c.id = p.customer_id
        JOIN asset a ON a.id = p.asset_id
        JOIN user u ON u.id = p.user_id
        ORDER BY p.protocol_date DESC, p.id DESC
        """
    ).fetchall()
    return render_template("protocols.html", rows=rows)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
