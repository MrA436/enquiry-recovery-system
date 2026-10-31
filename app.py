"""Enquiry Recovery System: a small Streamlit demo for managing customer enquiries."""

import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

import database as db

st.set_page_config(page_title="Enquiry Recovery System", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;}
    h1 {font-size: 1.75rem !important; font-weight: 650; letter-spacing: -0.01em; padding-bottom: .25rem;}
    h2, h3 {font-size: 1.1rem !important; font-weight: 600; padding-top: .5rem;}
    [data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 14px 18px;
    }
    [data-testid="stMetricLabel"] p {color: #6B7280; font-size: .85rem; white-space: normal;}
    [data-testid="stMetricValue"] {font-size: 1.9rem; font-weight: 600;}
    [data-testid="stForm"] {background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;}
    [data-testid="stSidebar"] {border-right: 1px solid #E5E7EB;}
    </style>
    """,
    unsafe_allow_html=True,
)

DATE_FORMAT = "DD/MM/YYYY"  # used by date inputs; tables use the same layout

LABELS = {
    "customer_name": "Customer", "phone": "Phone", "service": "Service",
    "enquiry_date": "Enquiry date", "status": "Status", "follow_up_date": "Follow-up date",
    "appointment_date": "Appointment", "notes": "Notes", "timing": "Timing",
}
WIDTHS = {  # fixed pixel widths so stacked tables line up column-for-column and nothing truncates
    "Customer": 175, "Phone": 95, "Service": 105, "Enquiry date": 115,
    "Status": 95, "Follow-up date": 125, "Appointment": 115,
    "Timing": 125, "Notes": "large",
}
STATUS_STYLE = {
    "New": "background-color:#DBEAFE;color:#1E40AF",
    "Contacted": "background-color:#F3F4F6;color:#374151",
    "Follow-up": "background-color:#FEF3C7;color:#92400E",
    "Booked": "background-color:#DCFCE7;color:#166534",
    "Lost": "background-color:#FEE2E2;color:#991B1B",
}


# --------------------------------------------------------------------------- helpers

def flash(kind, message):
    """Queue a message that survives the next rerun."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    item = st.session_state.pop("_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def fmt_date(value):
    if value is None or pd.isna(value):
        return "—"
    return date.fromisoformat(value).strftime("%d/%m/%Y")


def to_date(value):
    return date.fromisoformat(value) if isinstance(value, str) and value else None


def timing_labels(df, today):
    """'3 days overdue' / 'Today' / 'In 2 days' for each follow-up date."""
    out = []
    for value in df["follow_up_date"]:
        n = (date.fromisoformat(value) - today).days
        unit = "day" if abs(n) == 1 else "days"
        out.append("Today" if n == 0 else f"{-n} {unit} overdue" if n < 0 else f"In {n} {unit}")
    return out


def table(df, columns, today=None, select=False, key=None):
    """Read-only table with friendly labels, formatted dates and coloured status.

    If `today` is given, a Timing column is inserted after the follow-up date.
    Returns the selected row positions when `select` is True.
    """
    out = df[columns].copy() if len(df) else pd.DataFrame(columns=columns)
    for col in ("enquiry_date", "follow_up_date", "appointment_date"):
        if col in out:
            out[col] = out[col].map(fmt_date)
    if "notes" in out:
        out["notes"] = out["notes"].fillna("")
    if today is not None and len(df):
        out.insert(columns.index("follow_up_date") + 1, "timing", timing_labels(df, today))
    out = out.rename(columns=LABELS)

    shown = out.style.map(lambda v: STATUS_STYLE.get(v, ""), subset=["Status"]) if "Status" in out else out
    config = {c: st.column_config.TextColumn(width=WIDTHS.get(c, 120)) for c in out.columns}
    kwargs = {"on_select": "rerun", "selection_mode": "single-row", "key": key} if select else {}
    event = st.dataframe(shown, hide_index=True, width="stretch", column_config=config, **kwargs)
    return event.selection.rows if select else []


def sample_notice(df):
    if len(df) and df["is_sample"].any():
        st.caption("Names marked “(sample)” are fictional demonstration data.")


def display_names(df):
    """Mark sample rows so fictional data is always clearly labelled."""
    df = df.copy()
    df["customer_name"] = [f"{n} (sample)" if s else n for n, s in zip(df["customer_name"], df["is_sample"])]
    return df


# --------------------------------------------------------------------------- pages

def render_overview(df, today):
    st.title("Overview")
    st.caption(f"Today is {today.strftime('%A, %d %B %Y')}")

    m = db.get_metrics(today)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total enquiries", m["total"])
    c2.metric("To follow up", m["needs_follow_up"])
    c3.metric("Bookings", m["bookings"])
    c4.metric("Conversion rate", f"{m['conversion_rate']:.1f}%")

    if m["total"] == 0:
        st.info("No enquiries yet. Add one from the Enquiries section, or load the sample data below.")

    df = display_names(df)
    buckets = db.followup_buckets(df, today)

    st.subheader("Needs attention")
    urgent = pd.concat([buckets["overdue"], buckets["today"]])
    if urgent.empty:
        st.caption("No overdue or due-today follow-ups.")
    else:
        table(urgent, ["customer_name", "service", "status", "follow_up_date"], today)

    st.subheader("Booked appointments")
    booked = db.booked_appointments(df)
    if booked.empty:
        st.caption("No booked appointments yet.")
    else:
        table(booked, ["customer_name", "phone", "service", "appointment_date"])

    st.divider()
    st.subheader("Demo data")
    st.caption("Loads a small set of fictional enquiries with dates relative to today. Can only be loaded once.")
    loaded = db.sample_data_loaded()
    if st.button("Sample data loaded" if loaded else "Load sample data", disabled=loaded, key="load_sample"):
        count = db.load_sample_data(today)
        flash("success", f"Loaded {count} fictional sample enquiries.")
        st.rerun()


def render_new_enquiry_form(today):
    with st.form("new_enquiry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Customer name *", key="new_name")
        phone = col2.text_input("Phone number *", key="new_phone")
        service = col1.selectbox("Service requested *", db.SERVICES, key="new_service")
        enquiry_date = col2.date_input("Enquiry date *", value=today, format=DATE_FORMAT, key="new_date")
        notes = st.text_area("Additional notes (optional)", key="new_notes", height=100)
        submitted = st.form_submit_button("Save enquiry", type="primary")

    if submitted:
        try:
            lead_id = db.add_enquiry(name, phone, service, enquiry_date, notes)
        except db.ValidationError as exc:
            for message in exc.errors:
                st.error(message)
        except sqlite3.Error as exc:
            st.error(f"Could not save the enquiry: {exc}")
        else:
            flash("success", f"Enquiry #{lead_id} for {name.strip()} saved with status New.")
            st.rerun()


def render_update_form(lead):
    lead_id = int(lead["id"])
    st.subheader(f"Update lead: {lead['customer_name']}")
    with st.form(f"edit_lead_{lead_id}"):
        col1, col2, col3 = st.columns(3)
        status = col1.selectbox(
            "Status", db.STATUSES, index=db.STATUSES.index(lead["status"]), key=f"status_{lead_id}"
        )
        follow_up = col2.date_input(
            "Follow-up date", value=to_date(lead["follow_up_date"]), format=DATE_FORMAT,
            key=f"follow_{lead_id}", help="Required when the status is Follow-up.",
        )
        appointment = col3.date_input(
            "Appointment date", value=to_date(lead["appointment_date"]), format=DATE_FORMAT,
            key=f"appt_{lead_id}", help="Required when the status is Booked.",
        )
        notes = st.text_area("Notes", value=lead["notes"] or "", key=f"notes_{lead_id}", height=100)
        saved = st.form_submit_button("Save changes", type="primary")

    if saved:
        try:
            db.update_lead(lead_id, status, follow_up, appointment, notes)
        except db.ValidationError as exc:
            for message in exc.errors:
                st.error(message)
        except (ValueError, sqlite3.Error) as exc:
            st.error(f"Could not update the lead: {exc}")
        else:
            flash("success", f"Lead #{lead_id} ({lead['customer_name']}) updated.")
            st.rerun()


def render_enquiries(df, today):
    st.title("Enquiries")
    tab_all, tab_new = st.tabs(["All enquiries", "New enquiry"])
    with tab_all:
        if df.empty:
            st.info("No enquiries yet. Use the “New enquiry” tab, or load sample data from the Overview.")
            return
        df = display_names(df)
        st.caption("Select a row to update that lead.")
        rows = table(
            df, ["customer_name", "phone", "service", "enquiry_date", "status", "follow_up_date"],
            select=True, key="lead_table",
        )
        sample_notice(df)
        if rows:
            render_update_form(df.iloc[rows[0]])
    with tab_new:
        render_new_enquiry_form(today)


def render_followups(df, today):
    st.title("Follow-ups")
    st.caption("Reminders are display-only; no messages are sent. Booked and Lost leads are excluded.")
    df = display_names(df)
    buckets = db.followup_buckets(df, today)

    c1, c2, c3 = st.columns(3)
    c1.metric("Overdue", len(buckets["overdue"]))
    c2.metric("Due today", len(buckets["today"]))
    c3.metric("Upcoming", len(buckets["upcoming"]))

    for key, title in (("overdue", "Overdue"), ("today", "Due today"), ("upcoming", "Upcoming")):
        st.subheader(title)
        section = buckets[key]
        if section.empty:
            st.caption("Nothing here.")
        else:
            table(section, ["customer_name", "phone", "service", "status", "follow_up_date", "notes"], today)
    sample_notice(df)


# --------------------------------------------------------------------------- main

def main():
    today = date.today()
    try:
        db.init_db()
    except (sqlite3.Error, OSError) as exc:
        st.error(f"Could not open the database: {exc}")
        st.stop()

    with st.sidebar:
        st.markdown("### Enquiry Recovery")
        st.caption("Portfolio demo · fictional data only")
        page = st.radio("Navigate", ["Overview", "Enquiries", "Follow-ups"],
                        key="page", label_visibility="collapsed")

    show_flash()
    try:
        df = db.fetch_leads()
        {"Overview": render_overview, "Enquiries": render_enquiries, "Follow-ups": render_followups}[page](df, today)
    except sqlite3.Error as exc:
        st.error(f"Database error: {exc}")


main()