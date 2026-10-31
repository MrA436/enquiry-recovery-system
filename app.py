"""Enquiry Recovery System: a small Streamlit demo for managing customer enquiries."""

import html
import re
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

import database as db

st.set_page_config(page_title="Enquiry Recovery System", page_icon="📋", layout="wide")

# --------------------------------------------------------------------------- styling

THEMES = {
    "light": {
        "scheme": "light", "bg": "#F4F6FA", "surface": "#FFFFFF", "border": "#E6EAF0", "border2": "#EEF2F7",
        "row_line": "#F1F5F9", "head_bg": "#F8FAFC", "hover": "#FAFBFD", "text": "#0F172A", "text2": "#1E293B",
        "muted": "#64748B", "dim": "#94A3B8", "notes": "#475569", "chip_bg": "#F1F5F9", "chip_fg": "#475569",
        "shadow": "rgba(16,24,40,.04)", "sidebar": "#0F172A", "input_bg": "#FFFFFF", "tab_line": "#E2E8F0",
        "over": "#DC2626", "today": "#D97706", "soon": "#2563EB", "df_filter": "none",
    },
    "dark": {
        "scheme": "dark", "bg": "#0B1220", "surface": "#111A2E", "border": "#1F2A44", "border2": "#1A2440",
        "row_line": "#18223A", "head_bg": "#0E1628", "hover": "#16213A", "text": "#E6EAF2", "text2": "#D3DAE6",
        "muted": "#8A97AD", "dim": "#64748B", "notes": "#A9B6CC", "chip_bg": "#1B2742", "chip_fg": "#A9B6CC",
        "shadow": "rgba(0,0,0,.35)", "sidebar": "#080D18", "input_bg": "#0E1628", "tab_line": "#1F2A44",
        "over": "#F87171", "today": "#FBBF24", "soon": "#60A5FA", "df_filter": "invert(1) hue-rotate(180deg)",
    },
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root, .stApp {color-scheme: %(scheme)s;}
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp table
  {font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;}
[data-testid="stIconMaterial"], [data-testid="stIconMaterial"] * {font-family: 'Material Symbols Rounded' !important;}
.stApp {background: %(bg)s; color: %(text)s;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stHeader"] * {color: %(muted)s;}
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px;}
.stApp [data-testid="stMain"] p, .stApp [data-testid="stMain"] label, .stApp [data-testid="stMain"] li,
.stApp [data-testid="stMain"] h1, .stApp [data-testid="stMain"] h2, .stApp [data-testid="stMain"] h3 {color: %(text)s;}
[data-testid="stMain"] [data-testid="stCaptionContainer"], [data-testid="stMain"] [data-testid="stWidgetLabel"] p
  {color: %(muted)s;}

/* ---- sidebar ---- */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {background: %(sidebar)s; border-right: none;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] small {color: #94A3B8;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, [data-testid="stSidebar"] label p {color: #CBD5E1;}
[data-testid="stSidebar"] .stButton button {background: #1E293B; color: #E2E8F0; border: 1px solid #334155;}
[data-testid="stSidebar"] .stButton button:disabled {opacity: .55;}
.brand {display: flex; align-items: center; gap: 12px; padding: 6px 4px 18px;}
.brand-mark {width: 36px; height: 36px; border-radius: 10px; background: #6366F1; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1rem;}
.brand-name {color: #F8FAFC; font-weight: 650; font-size: 1rem; line-height: 1.2;}
.brand-sub {color: #94A3B8; font-size: .75rem;}
.side-label {color: #64748B; font-size: .68rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; margin: 22px 4px 8px;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
  padding: 9px 12px; border-radius: 8px; margin-bottom: 2px; width: 100%; cursor: pointer;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {background: #1E293B;}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {background: #312E81;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div:first-of-type > div:first-child {display: none;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {color: #CBD5E1; font-weight: 500; font-size: .92rem;}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {color: #FFFFFF;}

/* ---- page header ---- */
.ph-title {font-size: 1.65rem; font-weight: 700; color: %(text)s; letter-spacing: -.02em; line-height: 1.2;}
.ph-sub {color: %(muted)s; font-size: .9rem; margin: 4px 0 22px;}

/* ---- KPI cards ---- */
.kpi {background: %(surface)s; border: 1px solid %(border)s; border-radius: 14px; padding: 18px 20px;
  box-shadow: 0 1px 2px %(shadow)s; min-height: 118px;}
.kpi-top {display: flex; align-items: center; gap: 8px;}
.kpi-dot {width: 9px; height: 9px; border-radius: 50%%;}
.kpi-label {font-size: .8rem; color: %(muted)s; font-weight: 500;}
.kpi-value {font-size: 2.1rem; font-weight: 700; color: %(text)s; margin-top: 8px; line-height: 1.1;
  letter-spacing: -.02em;}
.kpi-sub {font-size: .75rem; color: %(dim)s; margin-top: 4px;}

/* ---- cards & tables ---- */
.card {background: %(surface)s; border: 1px solid %(border)s; border-radius: 14px; margin: 22px 0 0;
  box-shadow: 0 1px 2px %(shadow)s; overflow: hidden;}
.card-head {display: flex; align-items: center; gap: 10px; padding: 16px 20px; border-bottom: 1px solid %(border2)s;}
.card-title {font-size: .98rem; font-weight: 650; color: %(text)s;}
.count {background: %(chip_bg)s; color: %(chip_fg)s; font-size: .72rem; font-weight: 600;
  padding: 2px 9px; border-radius: 999px;}
.tbl-wrap {overflow-x: auto;}
table.t {width: 100%%; min-width: 780px; table-layout: fixed; border-collapse: collapse; font-size: .86rem; margin: 0; border: none;}
table.t th, table.t td {border-left: none !important; border-right: none !important; border-top: none !important;}
table.t th {text-align: left; font-size: .68rem; font-weight: 600; color: %(muted)s; letter-spacing: .06em;
  text-transform: uppercase; padding: 10px 20px; background: %(head_bg)s; border-bottom: 1px solid %(border2)s;
  white-space: nowrap;}
table.t td {padding: 13px 20px; border-bottom: 1px solid %(row_line)s; color: %(text2)s; vertical-align: middle;
  background: transparent;}
table.t tr:last-child td {border-bottom: none;}
table.t tr:hover td {background: %(hover)s;}
.who {display: flex; align-items: center; gap: 11px; white-space: nowrap;}
.av {width: 32px; height: 32px; border-radius: 50%%; display: inline-flex; align-items: center;
  justify-content: center; font-size: .72rem; font-weight: 650; flex: none;}
.nm {font-weight: 600; color: %(text)s;}
.tag {font-size: .62rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
  background: %(chip_bg)s; color: %(muted)s; padding: 2px 7px; border-radius: 6px;}
.pill {display: inline-flex; align-items: center; gap: 6px; font-size: .75rem; font-weight: 600;
  padding: 3px 10px; border-radius: 999px; white-space: nowrap;}
.pill i {width: 6px; height: 6px; border-radius: 50%%; display: inline-block;}
.muted {color: %(muted)s;}
.dim {color: %(dim)s;}
.notes {color: %(notes)s; max-width: 340px; min-width: 180px; line-height: 1.4;}
.when {font-size: .74rem; font-weight: 600; margin-top: 2px; white-space: nowrap;}
table.t td.c-phone, table.t td.c-service {white-space: nowrap;}
.when.over {color: %(over)s;} .when.today {color: %(today)s;} .when.soon {color: %(soon)s;}
.empty {padding: 30px 20px; text-align: center; color: %(dim)s; font-size: .88rem;}

/* ---- forms / widgets ---- */
[data-testid="stForm"] {background: %(surface)s; border: 1px solid %(border)s; border-radius: 14px; padding: 8px 10px;
  box-shadow: 0 1px 2px %(shadow)s;}
[data-testid="stMain"] [data-baseweb="input"], [data-testid="stMain"] [data-baseweb="textarea"],
[data-testid="stMain"] [data-baseweb="select"] > div, [data-testid="stMain"] [data-baseweb="base-input"]
  {background: %(input_bg)s !important; border-color: %(border)s !important; color: %(text)s;}
[data-testid="stMain"] input, [data-testid="stMain"] textarea, [data-testid="stMain"] [data-baseweb="select"] div
  {color: %(text)s !important; -webkit-text-fill-color: %(text)s;}
[data-testid="stMain"] input::placeholder, [data-testid="stMain"] textarea::placeholder
  {color: %(dim)s !important; -webkit-text-fill-color: %(dim)s;}
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] [data-baseweb="calendar"],
[data-baseweb="popover"] ul {background: %(surface)s !important; color: %(text)s;}
[data-baseweb="popover"] li, [data-baseweb="popover"] [role="option"], [data-baseweb="calendar"] *
  {color: %(text)s;}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [role="option"]:hover {background: %(hover)s !important;}
[data-testid="stMain"] [data-testid="stAlert"] {background: %(surface)s; border: 1px solid %(border)s;}
[data-testid="stMain"] [data-testid="stAlert"] * {color: %(text)s;}
[data-testid="stMain"] .stButton button[kind="secondary"], [data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"]
  {background: %(surface)s; color: %(text)s; border: 1px solid %(border)s;}
[data-testid="stDataFrame"] {filter: %(df_filter)s; border-radius: 10px;}
.stTabs [data-baseweb="tab-list"] {gap: 6px; border-bottom: 1px solid %(tab_line)s;}
.stTabs [data-baseweb="tab"] {font-weight: 600; padding: 8px 14px; color: %(muted)s;}
.stTabs [aria-selected="true"] {color: %(text)s;}
.lead-head {display: flex; align-items: center; gap: 12px; margin: 26px 0 12px;}
.lead-head .nm {font-size: 1.05rem;}
.hint {color: %(muted)s; font-size: .85rem; margin: 2px 0 10px;}
</style>
"""


def apply_theme(dark):
    theme = THEMES["dark" if dark else "light"]
    css = re.sub(r"%\((\w+)\)s", lambda m: theme[m.group(1)], CSS.replace("%%", "%"))
    st.markdown(css, unsafe_allow_html=True)


def is_dark():
    return st.session_state.get("dark_mode", True)


DATE_FORMAT = "DD/MM/YYYY"  # date inputs; tables use the same layout

STATUS_COLORS = {  # status: (background, text)
    "New": ("#EFF6FF", "#1D4ED8"),
    "Contacted": ("#F1F5F9", "#475569"),
    "Follow-up": ("#FFFBEB", "#B45309"),
    "Booked": ("#ECFDF5", "#047857"),
    "Lost": ("#FEF2F2", "#B91C1C"),
}
AVATARS = [("#E0E7FF", "#3730A3"), ("#FCE7F3", "#9D174D"), ("#DCFCE7", "#166534"),
           ("#FEF3C7", "#92400E"), ("#E0F2FE", "#075985"), ("#F3E8FF", "#6B21A8")]
STATUS_COLORS_DARK = {  # status: (background, text)
    "New": ("#16264A", "#7FB0FF"),
    "Contacted": ("#1E293B", "#B6C2D6"),
    "Follow-up": ("#3A2C0F", "#FBBF24"),
    "Booked": ("#0F3326", "#4ADE80"),
    "Lost": ("#3B1717", "#F87171"),
}
AVATARS_DARK = [("#27306B", "#C7D2FE"), ("#4A1D36", "#F9A8D4"), ("#143D27", "#86EFAC"),
                ("#44300E", "#FCD34D"), ("#0C3350", "#7DD3FC"), ("#3A1F5C", "#D8B4FE")]
HEADERS = {
    "customer_name": "Customer", "phone": "Phone", "service": "Service", "enquiry_date": "Enquiry date",
    "status": "Status", "follow_up_date": "Follow-up", "appointment_date": "Appointment", "notes": "Notes",
}
COL_WIDTHS = {"customer_name": "25%", "phone": "12%", "service": "14%", "enquiry_date": "14%",
              "status": "12%", "follow_up_date": "14%", "appointment_date": "14%"}  # notes takes the rest
NAV = {"Overview": "dashboard", "Enquiries": "inbox", "Follow-ups": "event_repeat"}


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


def esc(value):
    return html.escape("" if value is None or (not isinstance(value, str) and pd.isna(value)) else str(value))


def page_header(title, subtitle):
    st.markdown(f'<div class="ph-title">{esc(title)}</div><div class="ph-sub">{esc(subtitle)}</div>',
                unsafe_allow_html=True)


def kpi(label, value, sub, color):
    return (f'<div class="kpi"><div class="kpi-top"><span class="kpi-dot" style="background:{color}"></span>'
            f'<span class="kpi-label">{esc(label)}</span></div>'
            f'<div class="kpi-value">{esc(value)}</div><div class="kpi-sub">{esc(sub)}</div></div>')


def pill(status):
    colors = STATUS_COLORS_DARK if is_dark() else STATUS_COLORS
    bg, fg = colors.get(status, ("#1E293B", "#B6C2D6") if is_dark() else ("#F1F5F9", "#475569"))
    return f'<span class="pill" style="background:{bg};color:{fg}"><i style="background:{fg}"></i>{esc(status)}</span>'


def customer_cell(name, is_sample):
    palette = AVATARS_DARK if is_dark() else AVATARS
    bg, fg = palette[sum(map(ord, name)) % len(palette)]
    parts = name.split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"
    tag = ' <span class="tag">Sample</span>' if is_sample else ""
    return (f'<div class="who"><span class="av" style="background:{bg};color:{fg}">{esc(initials)}</span>'
            f'<span class="nm">{esc(name)}</span>{tag}</div>')


def when_label(value, today):
    n = (date.fromisoformat(value) - today).days
    unit = "day" if abs(n) == 1 else "days"
    if n < 0:
        return "over", f"{-n} {unit} overdue"
    return ("today", "Due today") if n == 0 else ("soon", f"In {n} {unit}")


def cell(row, col, today):
    if col == "customer_name":
        return customer_cell(row["customer_name"], bool(row["is_sample"]))
    if col == "status":
        return pill(row["status"])
    if col == "notes":
        return f'<div class="notes">{esc(row["notes"]) or "<span class=dim>—</span>"}</div>'
    if col == "phone":
        return f'<span class="muted">{esc(row["phone"])}</span>'
    if col == "follow_up_date":
        text = fmt_date(row["follow_up_date"])
        if today is not None and isinstance(row["follow_up_date"], str):
            cls, label = when_label(row["follow_up_date"], today)
            return f'{text}<div class="when {cls}">{label}</div>'
        return text if text != "—" else '<span class="dim">—</span>'
    if col in ("enquiry_date", "appointment_date"):
        text = fmt_date(row[col])
        return text if text != "—" else '<span class="dim">—</span>'
    return esc(row[col])


def card(title, df, columns, today=None, empty="Nothing here.", show_count=True):
    """A white card with a title, optional count badge and an HTML table (or an empty state)."""
    count = f'<span class="count">{len(df)}</span>' if show_count else ""
    head = f'<div class="card-head"><span class="card-title">{esc(title)}</span>{count}</div>'
    if df.empty:
        body = f'<div class="empty">{esc(empty)}</div>'
    else:
        colgroup = "<colgroup>" + "".join(
            f'<col style="width:{COL_WIDTHS[c]}">' if c in COL_WIDTHS else "<col>" for c in columns) + "</colgroup>"
        header = "".join(f"<th>{HEADERS[c]}</th>" for c in columns)
        rows = "".join(
            "<tr>" + "".join(f'<td class="c-{c}">{cell(r, c, today)}</td>' for c in columns) + "</tr>"
            for _, r in df.iterrows()
        )
        body = f'<div class="tbl-wrap"><table class="t">{colgroup}<thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'
    st.markdown(f'<div class="card">{head}{body}</div>', unsafe_allow_html=True)


def status_dataframe(df):
    """Selectable table for the Enquiries page (rows are clickable)."""
    out = pd.DataFrame({
        "Customer": [f"{n} (sample)" if s else n for n, s in zip(df["customer_name"], df["is_sample"])],
        "Phone": df["phone"], "Service": df["service"],
        "Enquiry date": df["enquiry_date"].map(fmt_date),
        "Status": df["status"], "Follow-up": df["follow_up_date"].map(fmt_date),
    })
    styled = out.style.map(
        lambda v: f"background-color:{STATUS_COLORS[v][0]};color:{STATUS_COLORS[v][1]};font-weight:600"
        if v in STATUS_COLORS else "", subset=["Status"])
    widths = {"Customer": 200, "Phone": 110, "Service": 120, "Enquiry date": 125, "Status": 110, "Follow-up": 125}
    config = {c: st.column_config.TextColumn(width=w) for c, w in widths.items()}
    event = st.dataframe(styled, hide_index=True, width="stretch", column_config=config,
                         on_select="rerun", selection_mode="single-row", key="lead_table")
    return event.selection.rows


# --------------------------------------------------------------------------- pages

def render_overview(df, today):
    m = db.get_metrics(today)
    page_header("Overview", f"{today.strftime('%A, %d %B %Y')}  ·  your enquiry pipeline at a glance")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Total enquiries", m["total"], "All time", "#6366F1"), unsafe_allow_html=True)
    c2.markdown(kpi("To follow up", m["needs_follow_up"], "Open leads needing contact", "#F59E0B"), unsafe_allow_html=True)
    c3.markdown(kpi("Bookings", m["bookings"], "Appointments booked", "#10B981"), unsafe_allow_html=True)
    c4.markdown(kpi("Conversion rate", f"{m['conversion_rate']:.1f}%", "Bookings ÷ enquiries", "#8B5CF6"),
                unsafe_allow_html=True)

    if m["total"] == 0:
        st.info("No enquiries yet. Add one in Enquiries, or use “Load sample data” in the sidebar.")

    buckets = db.followup_buckets(df, today)
    urgent = pd.concat([buckets["overdue"], buckets["today"]])
    card("Needs attention", urgent, ["customer_name", "service", "status", "follow_up_date"], today,
         empty="All caught up. Nothing overdue or due today.")
    card("Booked appointments", db.booked_appointments(df),
         ["customer_name", "phone", "service", "appointment_date"], empty="No booked appointments yet.")


def render_new_enquiry_form(today):
    with st.form("new_enquiry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Customer name *", key="new_name", placeholder="e.g. Jane Smith")
        phone = col2.text_input("Phone number *", key="new_phone", placeholder="e.g. 555-0123")
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
    st.markdown(
        f'<div class="lead-head">{customer_cell(lead["customer_name"], bool(lead["is_sample"]))}'
        f'{pill(lead["status"])}<span class="dim">Lead #{lead_id} · {esc(lead["service"])} · '
        f'{esc(lead["phone"])}</span></div>', unsafe_allow_html=True)
    with st.form(f"edit_lead_{lead_id}"):
        col1, col2, col3 = st.columns(3)
        status = col1.selectbox(
            "Status", db.STATUSES, index=db.STATUSES.index(lead["status"]), key=f"status_{lead_id}")
        follow_up = col2.date_input(
            "Follow-up date", value=to_date(lead["follow_up_date"]), format=DATE_FORMAT,
            key=f"follow_{lead_id}", help="Required when the status is Follow-up.")
        appointment = col3.date_input(
            "Appointment date", value=to_date(lead["appointment_date"]), format=DATE_FORMAT,
            key=f"appt_{lead_id}", help="Required when the status is Booked.")
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
    page_header("Enquiries", f"{len(df)} total  ·  select a row to update a lead")
    tab_all, tab_new = st.tabs(["All enquiries", "New enquiry"])
    with tab_all:
        if df.empty:
            st.info("No enquiries yet. Use the “New enquiry” tab, or load sample data from the sidebar.")
            return
        rows = status_dataframe(df)
        if df["is_sample"].any():
            st.markdown('<div class="hint">Names marked “(sample)” are fictional demonstration data.</div>',
                        unsafe_allow_html=True)
        if rows:
            render_update_form(df.iloc[rows[0]])
    with tab_new:
        render_new_enquiry_form(today)


def render_followups(df, today):
    page_header("Follow-ups", "Display-only reminders. No messages are sent. Booked and Lost leads are excluded.")
    buckets = db.followup_buckets(df, today)

    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi("Overdue", len(buckets["overdue"]), "Past their follow-up date", "#EF4444"), unsafe_allow_html=True)
    c2.markdown(kpi("Due today", len(buckets["today"]), "Contact today", "#F59E0B"), unsafe_allow_html=True)
    c3.markdown(kpi("Upcoming", len(buckets["upcoming"]), "Scheduled ahead", "#3B82F6"), unsafe_allow_html=True)

    columns = ["customer_name", "phone", "service", "status", "follow_up_date", "notes"]
    card("Overdue", buckets["overdue"], columns, today, empty="No overdue follow-ups.")
    card("Due today", buckets["today"], columns, today, empty="Nothing due today.")
    card("Upcoming", buckets["upcoming"], columns, today, empty="No upcoming follow-ups.")


# --------------------------------------------------------------------------- main

def main():
    today = date.today()
    try:
        db.init_db()
    except (sqlite3.Error, OSError) as exc:
        st.error(f"Could not open the database: {exc}")
        st.stop()

    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark">E</div><div>'
                    '<div class="brand-name">Enquiry Recovery</div>'
                    '<div class="brand-sub">Lead tracking demo</div></div></div>'
                    '<div class="side-label">Menu</div>', unsafe_allow_html=True)
        page = st.radio("Navigate", list(NAV), key="page", label_visibility="collapsed",
                        format_func=lambda p: f":material/{NAV[p]}: {p}")
        st.markdown('<div class="side-label">Demo data</div>', unsafe_allow_html=True)
        loaded = db.sample_data_loaded()
        if st.button("Sample data loaded" if loaded else "Load sample data", disabled=loaded,
                     key="load_sample", width="stretch"):
            count = db.load_sample_data(today)
            flash("success", f"Loaded {count} fictional sample enquiries.")
            st.rerun()
        st.caption("Sample enquiries are fictional and can only be loaded once.")
        st.markdown('<div class="side-label">Appearance</div>', unsafe_allow_html=True)
        st.toggle(":material/dark_mode: Dark mode", value=True, key="dark_mode")

    apply_theme(is_dark())

    show_flash()
    try:
        df = db.fetch_leads()
        {"Overview": render_overview, "Enquiries": render_enquiries, "Follow-ups": render_followups}[page](df, today)
    except sqlite3.Error as exc:
        st.error(f"Database error: {exc}")


main()