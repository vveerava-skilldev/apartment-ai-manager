import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sri Krishna Mani Apartments", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main-title { color: #1A365D; font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .sub-title { color: #4A5568; font-size: 16px; text-align: center; margin-bottom: 25px; }
    .alert-card { background-color: #FFF5F5; border-left: 5px solid #E53E3E; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px; }
    .metric-card { background-color: #F7FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE SETUP (SQLite with Audit Logs)
# -----------------------------------------------------------------------------
DB_FILE = "sri_krishna_mani.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Flats & Owner Master
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat TEXT PRIMARY KEY,
            owner_name TEXT,
            status TEXT,
            last_paid TEXT
        )
    """)
    
    # Configurable Global Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Fee Configuration Change History Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_config_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            old_amount REAL,
            new_amount REAL,
            changed_by TEXT,
            reason TEXT
        )
    """)

    # Payment Audit Trail
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            flat TEXT,
            amount REAL,
            payment_mode TEXT,
            txn_id TEXT
        )
    """)

    # Standard Expenses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL
        )
    """)

    # Corpus Pool & Operations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            flat_or_vendor TEXT,
            description TEXT,
            amount REAL
        )
    """)

    # Proposed Expenses (Approval Workflow)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposed_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            proposed_by TEXT,
            title TEXT,
            estimated_cost REAL,
            justification TEXT,
            status TEXT
        )
    """)

    # AMCs & Schedules
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS amc_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment TEXT,
            vendor TEXT,
            next_due TEXT,
            alert_days INTEGER
        )
    """)

    # Issues Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            flat TEXT,
            category TEXT,
            issue TEXT,
            status TEXT
        )
    """)

    # Meetings & MOM
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            title TEXT,
            attendees TEXT,
            summary_mom TEXT
        )
    """)

    # Seed Default Data
    cursor.execute("SELECT COUNT(*) FROM flats")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO flats VALUES (?, ?, ?, ?)", [
            ("101", "Sharma", "Paid", "2026-09-01"),
            ("102", "Verma", "Pending", "-"),
            ("201", "Rao", "Paid", "2026-09-03"),
            ("202", "Gupta", "Pending", "-"),
            ("301", "Patel", "Paid", "2026-09-05"),
        ])
        cursor.execute("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', '2000')")
        cursor.execute("INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason) VALUES (?, ?, ?, ?, ?)",
                       (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 0, 2000, "System Admin", "Initial Maintenance Rate Set"))
        
        cursor.executemany("INSERT INTO amc_schedules (equipment, vendor, next_due, alert_days) VALUES (?, ?, ?, ?)", [
            ("Water Softener System", "Zero B Care", "2026-10-15", 30),
            ("Lift / Elevator", "Otis India", "2026-09-25", 10),
            ("Water Tank Cleaning", "CleanAqua", "2026-09-22", 7)
        ])
        cursor.execute("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES ('2026-01-01', 'Contribution', 'All Flats', 'Initial Corpus Pool', 150000)")

    conn.commit()
    conn.close()

init_db()

def run_query(query, params=()):
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def get_current_maintenance_fee():
    df = run_query("SELECT value FROM settings WHERE key='monthly_maintenance'")
    return float(df.iloc[0]['value']) if not df.empty else 2000.0

# -----------------------------------------------------------------------------
# NAVIGATION & PERSONA SWITCHER
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Navigation")

flats_df = run_query("SELECT flat, owner_name FROM flats")
persona_list = ["All Residents (Public View)"] + [f"Flat {row['flat']} ({row['owner_name']})" for _, row in flats_df.iterrows()]
active_persona = st.sidebar.selectbox("👤 Active Persona:", persona_list)

current_flat = None
if active_persona != "All Residents (Public View)":
    current_flat = active_persona.split(" ")[1]

page = st.sidebar.radio("Go to:", [
    "📊 Public Dashboard",
    "💳 Maintenance Tracking & Payments",
    "🤖 AI Voice/Text Assistant",
    "🏛️ Corpus & Proposals",
    "📅 AMCs & Schedules",
    "🚨 Report Issue / Complaints",
    "📝 Meetings & Minutes (MOM)",
    "⚙️ Admin Control Panel"
])

st.sidebar.markdown("---")
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    admin_pass = st.sidebar.text_input("Admin Passcode", type="password")
    if st.sidebar.button("Login as Admin"):
        if admin_pass == "admin123":
            st.session_state.admin_logged_in = True
            st.sidebar.success("Logged in as Admin")
            st.rerun()
        else:
            st.sidebar.error("Incorrect Passcode")
else:
    st.sidebar.write("🟢 **Admin Mode Active**")
    if st.sidebar.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
st.markdown("<div class='main-title'>🏢 Sri Krishna Mani Apartments</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Co-operative Housing Management & Tracking Portal</div>", unsafe_allow_html=True)

monthly_fee = get_current_maintenance_fee()

# -----------------------------------------------------------------------------
# PAGE 1: PUBLIC DASHBOARD
# -----------------------------------------------------------------------------
if page == "📊 Public Dashboard":
    amcs = run_query("SELECT * FROM amc_schedules")
    active_alerts = []
    for _, amc in amcs.iterrows():
        due_date = datetime.strptime(amc["next_due"], "%Y-%m-%d").date()
        days_left = (due_date - datetime.now().date()).days
        if days_left <= amc["alert_days"]:
            active_alerts.append(f"⚠️ **{amc['equipment']} ({amc['vendor']})** service is due in **{days_left} days** (Due Date: {amc['next_due']})")

    if active_alerts:
        st.subheader("🔔 Active Dashboard Alerts")
        for alert in active_alerts:
            st.markdown(f"<div class='alert-card'>{alert}</div>", unsafe_allow_html=True)

    f_df = run_query("SELECT * FROM flats")
    e_df = run_query("SELECT SUM(amount) as total FROM expenses")
    c_df = run_query("SELECT SUM(CASE WHEN type='Contribution' THEN amount ELSE -amount END) as balance FROM corpus")

    paid_flats = (f_df["status"] == "Paid").sum()
    pending_flats = (f_df["status"] == "Pending").sum()
    pending_amount = pending_flats * monthly_fee
    total_spent = e_df["total"].iloc[0] if e_df["total"].iloc[0] else 0.0
    corpus_bal = c_df["balance"].iloc[0] if c_df["balance"].iloc[0] else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Maintenance Rate", f"₹{monthly_fee:,.0f} / mo")
    m2.metric("✅ Payment Progress", f"{paid_flats} Paid / {pending_flats} Pending")
    m3.metric("⚠️ Total Pending Dues", f"₹{pending_amount:,.0f}")
    m4.metric("🏛️ Corpus Pool Balance", f"₹{corpus_bal:,.0f}")

    st.markdown("---")

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📋 Flat Collection Status")
        st.dataframe(f_df, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("🧾 Recent Maintenance Expenses")
        exp_df = run_query("SELECT date, category, description, amount FROM expenses ORDER BY id DESC LIMIT 5")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 2: MAINTENANCE TRACKING & PAYMENTS
# -----------------------------------------------------------------------------
elif page == "💳 Maintenance Tracking & Payments":
    st.title("💳 Monthly Maintenance Portal")
    st.info(f"Current Configured Rate: **₹{monthly_fee:,.2f} / month** per flat.")

    t1, t2, t3 = st.tabs(["💳 Pay / Update Status", "📜 Payment History Log", "⚙️ Config & Rate Revision History"])

    with t1:
        st.subheader("Make or Record Maintenance Payment")
        selected_flat = st.selectbox("Select Flat Number:", ["101", "102", "201", "202", "301"], 
                                     index=["101", "102", "201", "202", "301"].index(current_flat) if current_flat else 0)
        
        flat_status_df = run_query("SELECT * FROM flats WHERE flat=?", (selected_flat,))
        flat_info = flat_status_df.iloc[0]

        st.write(f"**Flat Owner:** {flat_info['owner_name']}")
        st.write(f"**Current Status:** {flat_info['status']}")
        st.write(f"**Amount Due:** ₹{0.0 if flat_info['status'] == 'Paid' else monthly_fee:,.2f}")

        if flat_info['status'] == "Pending":
            with st.form("pay_form"):
                pay_mode = st.selectbox("Payment Method", ["UPI / QR", "Net Banking", "Cash / Cheque"])
                ref_id = st.text_input("Transaction / Reference ID", placeholder="e.g. UPI/123456789")
                if st.form_submit_button("Submit Payment"):
                    now_str = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
                    execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (now_str, selected_flat))
                    execute_db("INSERT INTO payment_history (timestamp, flat, amount, payment_mode, txn_id) VALUES (?, ?, ?, ?, ?)",
                               (now_str, selected_flat, monthly_fee, pay_mode, ref_id))
                    st.success(f"Payment of ₹{monthly_fee} recorded for Flat {selected_flat}!")
                    st.rerun()
        else:
            st.success("✅ Maintenance paid for this cycle.")

    with t2:
        st.subheader("Historical Payment Audit Log")
        history_df = run_query("SELECT timestamp as Date, flat as 'Flat No', amount as Amount, payment_mode as Method, txn_id as 'Txn Ref' FROM payment_history ORDER BY id DESC")
        st.dataframe(history_df, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Maintenance Rate Revision History")
        st.caption("Tracks all historical revisions to the monthly maintenance amount.")
        rev_df = run_query("SELECT timestamp as Date, old_amount as 'Old Rate (₹)', new_amount as 'New Rate (₹)', changed_by as 'Changed By', reason as Reason FROM maintenance_config_history ORDER BY id DESC")
        st.dataframe(rev_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 3: AI VOICE / TEXT COMMAND
# -----------------------------------------------------------------------------
elif page == "🤖 AI Voice/Text Assistant":
    st.title("🤖 Voice & Text Command Assistant")
    cmd_input = st.text_input("🎙️ Command Prompt:", placeholder="e.g., Flat 102 paid monthly maintenance")
    if st.button("Execute Command") and cmd_input:
        cmd = cmd_input.lower()
        if "paid" in cmd or "payment" in cmd:
            match = re.search(r'\b(101|102|201|202|301)\b', cmd)
            if match:
                flat_no = match.group(1)
                now_str = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
                execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (now_str, flat_no))
                execute_db("INSERT INTO payment_history (timestamp, flat, amount, payment_mode, txn_id) VALUES (?, ?, ?, ?, ?)",
                           (now_str, flat_no, monthly_fee, "Voice Assistant", "AUTO-VOICE-CMD"))
                st.success(f"🤖 Database Updated: Flat {flat_no} marked as Paid (₹{monthly_fee}).")
            else:
                st.error("🤖 Could not find a valid flat number (101, 102, 201, 202, 301).")

# -----------------------------------------------------------------------------
# PAGE 4: CORPUS & PROPOSALS
# -----------------------------------------------------------------------------
elif page == "🏛️ Corpus & Proposals":
    st.title("🏛️ Corpus Fund & Expense Proposals")
    t1, t2 = st.tabs(["🏛️ Corpus Ledger", "💡 Propose New Expense"])
    with t1:
        st.dataframe(run_query("SELECT date, type, flat_or_vendor, description, amount FROM corpus ORDER BY id DESC"), use_container_width=True, hide_index=True)
    with t2:
        with st.form("propose_form"):
            proposer = current_flat if current_flat else st.selectbox("Proposing Flat", ["101", "102", "201", "202", "301"])
            title = st.text_input("Proposal Title")
            est_cost = st.number_input("Estimated Cost (₹)", min_value=100.0, step=500.0)
            justification = st.text_area("Justification")
            if st.form_submit_button("Submit Proposal"):
                execute_db("INSERT INTO proposed_expenses (date, proposed_by, title, estimated_cost, justification, status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                           (str(datetime.now().date()), proposer, title, est_cost, justification))
                st.success("Proposal submitted!")

        st.dataframe(run_query("SELECT id, date, proposed_by, title, estimated_cost, justification, status FROM proposed_expenses ORDER BY id DESC"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 5: AMCS
# -----------------------------------------------------------------------------
elif page == "📅 AMCs & Schedules":
    st.title("📅 AMCs & Equipment Schedules")
    st.dataframe(run_query("SELECT * FROM amc_schedules"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 6: REPORT ISSUES
# -----------------------------------------------------------------------------
elif page == "🚨 Report Issue / Complaints":
    st.title("🚨 Community Issue Portal")
    with st.form("issue_form"):
        reporter = current_flat if current_flat else st.selectbox("Select Flat", ["101", "102", "201", "202", "301"])
        cat = st.selectbox("Category", ["Plumbing", "Electrical", "Elevator", "Water Softener", "Common Area"])
        desc = st.text_area("Issue Description")
        if st.form_submit_button("Log Issue"):
            execute_db("INSERT INTO issues (date, flat, category, issue, status) VALUES (?, ?, ?, ?, 'Open')",
                       (str(datetime.now().date()), reporter, cat, desc))
            st.success("Issue logged!")
    st.dataframe(run_query("SELECT * FROM issues ORDER BY id DESC"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 7: MEETINGS & MINUTES (MOM)
# -----------------------------------------------------------------------------
elif page == "📝 Meetings & Minutes (MOM)":
    st.title("📝 Meetings & MOM")
    st.dataframe(run_query("SELECT date, title, attendees, summary_mom FROM meetings ORDER BY id DESC"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 8: ADMIN CONTROL PANEL
# -----------------------------------------------------------------------------
elif page == "⚙️ Admin Control Panel":
    st.title("⚙️ Admin Control Panel")
    if not st.session_state.admin_logged_in:
        st.warning("🔒 Admin Passcode Required.")
    else:
        a1, a2, a3, a4, a5 = st.tabs(["⚙️ Configure Fee Rate", "Approvals", "Corpus Ops", "Record MOM", "Database Export"])

        # Tab 1: Configure Fee
        with a1:
            st.subheader("Configure Monthly Maintenance Rate")
            st.write(f"Current Monthly Rate: **₹{monthly_fee:,.2f}**")
            with st.form("config_fee_form"):
                new_rate = st.number_input("New Monthly Rate (₹)", min_value=0.0, value=monthly_fee, step=100.0)
                revision_reason = st.text_area("Reason for Rate Revision")
                if st.form_submit_button("Update & Log Revision"):
                    if new_rate != monthly_fee:
                        now_str = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        execute_db("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', ?)", (str(new_rate),))
                        execute_db("INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason) VALUES (?, ?, ?, ?, ?)",
                                   (now_str, monthly_fee, new_rate, "Admin", revision_reason))
                        st.success(f"Maintenance rate revised to ₹{new_rate}! Change recorded in audit history.")
                        st.rerun()

        # Tab 2: Approvals
        with a2:
            pending_props = run_query("SELECT * FROM proposed_expenses WHERE status='Pending'")
            if pending_props.empty:
                st.info("No pending proposals.")
            else:
                for _, prop in pending_props.iterrows():
                    st.write(f"**{prop['title']}** — ₹{prop['estimated_cost']}")
                    ca, cr = st.columns(2)
                    if ca.button("Approve", key=f"a_{prop['id']}"):
                        execute_db("UPDATE proposed_expenses SET status='Approved' WHERE id=?", (prop['id'],))
                        st.rerun()
                    if cr.button("Reject", key=f"r_{prop['id']}"):
                        execute_db("UPDATE proposed_expenses SET status='Rejected' WHERE id=?", (prop['id'],))
                        st.rerun()

        # Tab 3: Corpus Ops
        with a3:
            with st.form("corpus_form"):
                c_type = st.selectbox("Type", ["Contribution", "Expenditure"])
                c_party = st.text_input("Source/Vendor")
                c_desc = st.text_input("Description")
                c_amt = st.number_input("Amount (₹)", min_value=1.0)
                if st.form_submit_button("Record Entry"):
                    execute_db("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES (?, ?, ?, ?, ?)",
                               (str(datetime.now().date()), c_type, c_party, c_desc, c_amt))
                    st.success("Corpus updated!")

        # Tab 4: MOM
        with a4:
            with st.form("mom_form"):
                m_title = st.text_input("Title")
                m_att = st.text_input("Attendees")
                m_summary = st.text_area("Summary")
                if st.form_submit_button("Save MOM"):
                    execute_db("INSERT INTO meetings (date, title, attendees, summary_mom) VALUES (?, ?, ?, ?)",
                               (str(datetime.now().date()), m_title, m_att, m_summary))
                    st.success("MOM recorded!")

        # Tab 5: Export
        with a5:
            with open(DB_FILE, "rb") as fp:
                st.download_button("💾 Download Database File (.db)", fp, file_name="sri_krishna_mani.db", mime="application/x-sqlite3")
