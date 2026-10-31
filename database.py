"""SQLite data layer for the Enquiry Recovery System.

All SQL lives here. Dates are stored as ISO strings (YYYY-MM-DD), which sort
and compare correctly as text, so follow-up categories can be calculated
reliably from the stored values.
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path(os.environ.get("ENQUIRY_DB_PATH", Path(__file__).parent / "enquiries.db"))

STATUSES = ["New", "Contacted", "Follow-up", "Booked", "Lost"]
OPEN_STATUSES = ["New", "Contacted", "Follow-up"]  # leads still being worked
SERVICES = ["Plumbing", "Electrical", "Cleaning", "HVAC", "Landscaping", "Painting", "Roofing", "Other"]

COLUMNS = [
    "id", "customer_name", "phone", "service", "enquiry_date", "status",
    "follow_up_date", "appointment_date", "notes", "is_sample", "created_at",
]

_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,25}$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name    TEXT NOT NULL,
    phone            TEXT NOT NULL,
    service          TEXT NOT NULL,
    enquiry_date     TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'New'
                     CHECK (status IN ('New','Contacted','Follow-up','Booked','Lost')),
    follow_up_date   TEXT,
    appointment_date TEXT,
    notes            TEXT,
    is_sample        INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_enquiries_status ON enquiries(status);
CREATE INDEX IF NOT EXISTS idx_enquiries_followup ON enquiries(follow_up_date);
"""


class ValidationError(ValueError):
    """Raised when user input fails validation. `errors` holds readable messages."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the database and table if they do not exist."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)


# --------------------------------------------------------------------------- helpers

def _iso(value):
    """Convert a date/datetime/ISO string/None to an ISO date string or None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError([f"Invalid date: {value!r}"])


def _clean(text):
    text = (text or "").strip()
    return text or None


# --------------------------------------------------------------------------- validation

def validate_enquiry(name, phone, service, enquiry_date):
    """Return a list of error messages (empty list means valid)."""
    errors = []
    name, phone, service = (name or "").strip(), (phone or "").strip(), (service or "").strip()

    if not name:
        errors.append("Customer name is required.")
    elif len(name) > 100:
        errors.append("Customer name must be 100 characters or fewer.")

    if not phone:
        errors.append("Phone number is required.")
    elif not _PHONE_RE.match(phone) or sum(c.isdigit() for c in phone) < 7:
        errors.append("Enter a valid phone number (at least 7 digits; digits, spaces, + - ( ) allowed).")

    if not service:
        errors.append("Service requested is required.")

    if enquiry_date is None or enquiry_date == "":
        errors.append("Enquiry date is required.")
    return errors


def validate_update(status, follow_up_date, appointment_date):
    errors = []
    if status not in STATUSES:
        errors.append(f"Status must be one of: {', '.join(STATUSES)}.")
    if status == "Booked" and not appointment_date:
        errors.append("An appointment date is required when the status is Booked.")
    if status == "Follow-up" and not follow_up_date:
        errors.append("A follow-up date is required when the status is Follow-up.")
    return errors


# --------------------------------------------------------------------------- writes

def add_enquiry(customer_name, phone, service, enquiry_date, notes=None, *, _sample=False,
                status="New", follow_up_date=None, appointment_date=None):
    """Validate and insert a new enquiry (status 'New'). Returns the new lead ID."""
    errors = validate_enquiry(customer_name, phone, service, enquiry_date)
    if errors:
        raise ValidationError(errors)
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO enquiries
               (customer_name, phone, service, enquiry_date, status,
                follow_up_date, appointment_date, notes, is_sample)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_name.strip(), phone.strip(), service.strip(), _iso(enquiry_date), status,
             _iso(follow_up_date), _iso(appointment_date), _clean(notes), 1 if _sample else 0),
        )
        return cur.lastrowid


def update_lead(lead_id, status, follow_up_date=None, appointment_date=None, notes=None):
    """Update a lead's status, follow-up date, appointment date and notes.

    The appointment date is only kept when the status is Booked.
    """
    follow_up_iso, appointment_iso = _iso(follow_up_date), _iso(appointment_date)
    errors = validate_update(status, follow_up_iso, appointment_iso)
    if errors:
        raise ValidationError(errors)
    if status != "Booked":
        appointment_iso = None
    with _connect() as conn:
        cur = conn.execute(
            """UPDATE enquiries
               SET status = ?, follow_up_date = ?, appointment_date = ?, notes = ?
               WHERE id = ?""",
            (status, follow_up_iso, appointment_iso, _clean(notes), int(lead_id)),
        )
        if cur.rowcount == 0:
            raise ValueError("That lead no longer exists.")


# --------------------------------------------------------------------------- reads

def fetch_leads():
    """All enquiries as a DataFrame, newest enquiry first. Always has COLUMNS."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM enquiries ORDER BY enquiry_date DESC, id DESC"
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows], columns=COLUMNS)


def get_metrics(today=None):
    """Dashboard metrics, calculated from the database."""
    today = _iso(today or date.today())
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
        bookings = conn.execute("SELECT COUNT(*) FROM enquiries WHERE status = 'Booked'").fetchone()[0]
        needs_follow_up = conn.execute(
            """SELECT COUNT(*) FROM enquiries
               WHERE status IN ('New','Contacted','Follow-up')
                 AND (status = 'Follow-up'
                      OR (follow_up_date IS NOT NULL AND follow_up_date <= ?))""",
            (today,),
        ).fetchone()[0]
    return {
        "total": total,
        "needs_follow_up": needs_follow_up,
        "bookings": bookings,
        "conversion_rate": (bookings / total * 100) if total else 0.0,
    }


def followup_buckets(df, today=None):
    """Split open leads that have a follow-up date into overdue / due today / upcoming."""
    iso = _iso(today or date.today())
    open_df = df[df["status"].isin(OPEN_STATUSES) & df["follow_up_date"].notna()]
    due = open_df["follow_up_date"]
    return {
        "overdue": open_df[due < iso].sort_values("follow_up_date"),
        "today": open_df[due == iso],
        "upcoming": open_df[due > iso].sort_values("follow_up_date"),
    }


def booked_appointments(df):
    booked = df[df["status"] == "Booked"]
    return booked.sort_values("appointment_date", na_position="last")


# --------------------------------------------------------------------------- sample data

def sample_data_loaded():
    with _connect() as conn:
        return conn.execute("SELECT 1 FROM enquiries WHERE is_sample = 1 LIMIT 1").fetchone() is not None


def load_sample_data(today=None):
    """Insert fictional demo enquiries once. Returns the number inserted (0 if already loaded)."""
    if sample_data_loaded():
        return 0
    today = today or date.today()
    d = lambda offset: today + timedelta(days=offset)  # noqa: E731

    samples = [
        # name, phone, service, enquiry, status, follow-up, appointment, notes
        ("Priya Sharma", "555-0101", "Plumbing", d(0), "New", None, None,
         "Leaking kitchen tap, wants a quote."),
        ("Marcus Hill", "555-0102", "Electrical", d(-8), "Follow-up", d(-3), None,
         "Needs 4 extra sockets. Called once, no answer."),
        ("Sofia Alvarez", "555-0103", "Cleaning", d(-5), "Follow-up", d(0), None,
         "Deep clean before moving out. Asked us to call back today."),
        ("Daniel Okafor", "555-0104", "HVAC", d(-3), "Contacted", d(4), None,
         "Annual AC service. Waiting for landlord approval."),
        ("Grace Whitfield", "555-0105", "Roofing", d(-10), "Booked", None, d(6),
         "Roof inspection confirmed."),
        ("Tom Becker", "555-0106", "Painting", d(-14), "Lost", None, None,
         "Chose another provider on price."),
        ("Hannah Lee", "555-0107", "Landscaping", d(-2), "Follow-up", d(2), None,
         "Garden redesign. Sent a rough estimate."),
    ]
    for name, phone, service, enq, status, follow_up, appt, notes in samples:
        add_enquiry(name, phone, service, enq, notes, _sample=True, status=status,
                    follow_up_date=follow_up, appointment_date=appt)
    return len(samples)
