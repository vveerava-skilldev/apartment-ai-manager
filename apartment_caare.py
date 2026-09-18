import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import re

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sri Krishna Mani Apartments", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .main-title {
        color: #1A365D;
        font-size: 36px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-title {
        color: #4A5568;
        font-size: 16px;
        text-align: center;
        margin-bottom: 25px;
    }
    .alert-card {
        background-color: #FFF5F5;
        border-left: 5px solid #E53E3E;
        padding: 12px 18px;
        border-radius: 4px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE SETUP (SQLite Dynamic Storage)
# -----------------------------------------------------------------------------
DB_FILE = "sri_krishna_mani.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Flats & Persona Master
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat TEXT PRIMARY KEY,
            owner_name TEXT,
            monthly_due REAL,
            status TEXT,
            last_paid TEXT
        )
    """)
    
    # Standard Maintenance Expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL
        )
    """)

    # Corpus Fund Registry & Expenditures
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT, -- 'Contribution' or 'Expenditure'
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
            status TEXT -- 'Pending', 'Approved', 'Rejected'
        )
    """)

    # AMCs & Maintenance Schedules
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

    # Meetings & Minutes (MOM)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            title TEXT,
            attendees TEXT,
            summary_mom TEXT
        )
    """)

    # Seed initial data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM flats")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO flats VALUES (?, ?, ?, ?, ?)", [
            ("101", "Sharma", 1000, "Paid", "2026-09-01"),
            ("102", "Verma", 1000, "Pending", "-"),
            ("201", "Rao", 1000, "Paid", "2026-09-03"),
            ("202", "Gupta", 1000, "Pending", "-"),
            ("301", "Patel", 1000, "Paid", "2026-09-05"),
        ])
        cursor.executemany("INSERT INTO amc_schedules (equipment, vendor, next_due, alert_days) VALUES (?, ?, ?, ?)", [
            ("Water Softener System", "Zero B Care", "2026-10-15", 30),
            ("Lift / Elevator", "Otis India", "2026-09-25", 10),
            ("Water Tank Cleaning", "CleanAqua", "2026-09-22", 7)
        ])
        cursor.execute("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES ('2026-01-01', 'Contribution', 'All Flats', 'Initial Corpus Pool', 150000)")
    
    conn.commit()
    conn.close()

init_db()

# Helper DB Functions
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

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION & PERSONA SWITCHER
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Navigation")

# Persona Selection
flats_df = run_query("SELECT flat, owner_name FROM flats")
persona_list = ["All Residents (Public View)"] + [f"Flat {row['flat']} ({row['owner_name']})" for _, row in flats_df.iterrows()]
active_persona = st.sidebar.selectbox("👤 Active User Persona:", persona_list)

current_flat = None
if active_persona != "All Residents (Public View)":
    current_flat = active_persona.split(" ")[1]

# Navigation Pages
page = st.sidebar.radio("Go to:", [
    "📊 Public Dashboard",
    "🤖 AI Voice/Text Command",
    "🏛️ Corpus & Proposed Expenses",
    "📅 AMCs & Tank Cleaning",
    "🚨 Report Issue / Complaints",
    "📝 Meetings & Minutes (MOM)",
    "⚙️ Admin Control Panel"
])

# Admin Authentication
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
# HEADER SECTION
# -----------------------------------------------------------------------------
st.markdown("<div class='main-title'>🏢 Sri Krishna Mani Apartments</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>5-Flat Co-operative Housing Management System</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PAGE 1: PUBLIC DASHBOARD WITH DYNAMIC ALERTS
# -----------------------------------------------------------------------------
if page == "📊 Public Dashboard":
    
    # Check Alerts (AMCs & Pending Dues)
    amcs = run_query("SELECT * FROM amc_schedules")
    active_alerts = []
    for _, amc in amcs.iterrows():
        due_date = datetime.strptime(amc["next_due"], "%Y-%m-%d").date()
        days_left = (due_date - datetime.now().date()).days
        if days_left <= amc["alert_days"]:
            active_alerts.append(f"⚠️ **{amc['equipment']} ({amc['vendor']})** service is due in **{days_left} days** (Due Date: {amc['next_due']})")

    # Render Alerts
    if active_alerts:
        st.subheader("🔔 Active System Alerts")
        for alert in active_alerts:
            st.markdown(f"<div class='alert-card'>{alert}</div>", unsafe_allow_html=True)

    # Metrics Overview
    f_df = run_query("SELECT * FROM flats")
    e_df = run_query("SELECT SUM(amount) as total FROM expenses")
    c_df = run_query("SELECT SUM(CASE WHEN type='Contribution' THEN amount ELSE -amount END) as balance FROM corpus")

    paid_flats = (f_df["status"] == "Paid").sum()
    pending_amount = f_df[f_df["status"] == "Pending"]["monthly_due"].sum()
    total_spent = e_df["total"].iloc[0] if e_df["total"].iloc[0] else 0.0
    corpus_bal = c_df["balance"].iloc[0] if c_df["balance"].iloc[0] else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Corpus Balance", f"₹{corpus_bal:,.0f}")
    m2.metric("✅ Flats Paid", f"{paid_flats} / 5")
    m3.metric("⚠️ Pending Dues", f"₹{pending_amount:,.0f}")
    m4.metric("📉 Expenses Logged", f"₹{total_spent:,.0f}")

    st.markdown("---")

    # Persona-Specific View
    if current_flat:
        st.info(f"👤 Showing tailored status for **Flat {current_flat}**")
        flat_info = f_df[f_df["flat"] == current_flat].iloc[0]
        c_left, c_right = st.columns(2)
        c_left.write(f"**Owner:** {flat_info['owner_name']}")
        c_left.write(f"**Monthly Maintenance Status:** {flat_info['status']}")
        c_right.write(f"**Due Amount:** ₹{flat_info['monthly_due']}")
        c_right.write(f"**Last Paid Date:** {flat_info['last_paid']}")
        st.markdown("---")

    # General Tables
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📋 Maintenance Collection Status")
        st.dataframe(f_df, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("🧾 Recent Expenses")
        exp_df = run_query("SELECT date, category, description, amount FROM expenses ORDER BY id DESC LIMIT 5")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 2: AI VOICE / TEXT COMMAND
# -----------------------------------------------------------------------------
elif page == "🤖 AI Voice/Text Command":
    st.title("🤖 Voice & Text Command Assistant")
    st.caption("Enter text commands or use smartphone microphone dictation.")

    cmd_input = st.text_input("🎙️ Command Prompt:", placeholder="e.g., Flat 102 paid monthly maintenance")
    if st.button("Execute Command") and cmd_input:
        cmd = cmd_input.lower()

        # Parse Payment
        if "paid" in cmd or "payment" in cmd:
            match = re.search(r'\b(101|102|201|202|301)\b', cmd)
            if match:
                flat_no = match.group(1)
                execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (str(datetime.now().date()), flat_no))
                st.success(f"🤖 Database Updated: Marked Flat {flat_no} as Paid.")
            else:
                st.error("🤖 Could not find a valid flat number (101, 102, 201, 202, 301).")

        # Parse Expense
        elif "expense" in cmd or "spent" in cmd or "logged" in cmd:
            amt_match = re.search(r'\b(\d+)\b', cmd)
            amt = float(amt_match.group(1)) if amt_match else 0.0
            cat = "General"
            if "watchman" in cmd: cat = "Watchman Fee"
            elif "tank" in cmd: cat = "Tank Cleaning"
            elif "electricity" in cmd: cat = "Common Power"
            
            execute_db("INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)", 
                       (str(datetime.now().date()), cat, cmd_input, amt))
            st.success(f"🤖 Database Updated: Added expense ₹{amt} under '{cat}'.")

# -----------------------------------------------------------------------------
# PAGE 3: CORPUS & PROPOSED EXPENSES WORKFLOW
# -----------------------------------------------------------------------------
elif page == "🏛️ Corpus & Proposed Expenses":
    st.title("🏛️ Corpus Fund & Expense Proposals")

    t1, t2 = st.tabs(["🏛️ Corpus Ledger", "💡 Propose New Expense"])

    with t1:
        st.subheader("Corpus Fund Ledger")
        corpus_df = run_query("SELECT date, type, flat_or_vendor, description, amount FROM corpus ORDER BY id DESC")
        st.dataframe(corpus_df, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Propose a Major Expense for Society Approval")
        with st.form("propose_form"):
            proposer = current_flat if current_flat else st.selectbox("Proposing Flat", ["101", "102", "201", "202", "301"])
            title = st.text_input("Proposal Title / Title of Work")
            est_cost = st.number_input("Estimated Cost (₹)", min_value=100.0, step=500.0)
            justification = st.text_area("Justification / Why is this needed?")
            
            if st.form_submit_button("Submit Proposal"):
                execute_db("INSERT INTO proposed_expenses (date, proposed_by, title, estimated_cost, justification, status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                           (str(datetime.now().date()), proposer, title, est_cost, justification))
                st.success("Proposal submitted successfully for Admin review!")

        st.markdown("---")
        st.subheader("📋 All Submitted Proposals & Status")
        prop_df = run_query("SELECT id, date, proposed_by, title, estimated_cost, justification, status FROM proposed_expenses ORDER BY id DESC")
        st.dataframe(prop_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 4: AMCS & TANK CLEANING
# -----------------------------------------------------------------------------
elif page == "📅 AMCs & Tank Cleaning":
    st.title("📅 Equipment Maintenance & AMC Tracker")
    amcs = run_query("SELECT * FROM amc_schedules")
    st.dataframe(amcs, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 5: REPORT COMPLAINTS & ISSUES
# -----------------------------------------------------------------------------
elif page == "🚨 Report Issue / Complaints":
    st.title("🚨 Resident Issue Reporting Portal")
    
    with st.form("issue_form"):
        reporter = current_flat if current_flat else st.selectbox("Select Flat", ["101", "102", "201", "202", "301"])
        cat = st.selectbox("Category", ["Plumbing", "Electrical", "Elevator", "Water Softener", "Common Area"])
        desc = st.text_area("Issue Description")
        
        if st.form_submit_button("Log Issue"):
            execute_db("INSERT INTO issues (date, flat, category, issue, status) VALUES (?, ?, ?, ?, 'Open')",
                       (str(datetime.now().date()), reporter, cat, desc))
            st.success("Issue logged successfully!")

    st.markdown("---")
    st.subheader("📋 Registered Community Issues")
    st.dataframe(run_query("SELECT * FROM issues ORDER BY id DESC"), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 6: MEETINGS & MINUTES (MOM)
# -----------------------------------------------------------------------------
elif page == "📝 Meetings & Minutes (MOM)":
    st.title("📝 Society Meetings & Minutes")
    
    m_df = run_query("SELECT date, title, attendees, summary_mom FROM meetings ORDER BY id DESC")
    st.dataframe(m_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 7: ADMIN CONTROL PANEL (Privileged Actions)
# -----------------------------------------------------------------------------
elif page == "⚙️ Admin Control Panel":
    st.title("⚙️ Administrative Control Panel")

    if not st.session_state.admin_logged_in:
        st.warning("🔒 Admin Passcode Required. Please log in using the sidebar.")
    else:
        a_tab1, a_tab2, a_tab3, a_tab4 = st.tabs(["Approvals", "Corpus Management", "Log Meeting MOM", "Database Export"])

        # Admin Tab 1: Approve Expenses
        with a_tab1:
            st.subheader("Approve / Reject Proposed Expenses")
            pending_props = run_query("SELECT * FROM proposed_expenses WHERE status='Pending'")
            if pending_props.empty:
                st.info("No pending proposals for review.")
            else:
                for _, prop in pending_props.iterrows():
                    st.write(f"**{prop['title']}** (Proposed by Flat {prop['proposed_by']}) — Estimated Cost: ₹{prop['estimated_cost']}")
                    st.caption(f"Justification: {prop['justification']}")
                    col_a, col_r = st.columns(2)
                    if col_a.button("Approve", key=f"app_{prop['id']}"):
                        execute_db("UPDATE proposed_expenses SET status='Approved' WHERE id=?", (prop['id'],))
                        st.success("Proposal Approved!")
                        st.rerun()
                    if col_r.button("Reject", key=f"rej_{prop['id']}"):
                        execute_db("UPDATE proposed_expenses SET status='Rejected' WHERE id=?", (prop['id'],))
                        st.warning("Proposal Rejected.")
                        st.rerun()

        # Admin Tab 2: Corpus Operations
        with a_tab2:
            st.subheader("Record Corpus Entry")
            with st.form("corpus_form"):
                c_type = st.selectbox("Transaction Type", ["Contribution", "Expenditure"])
                c_party = st.text_input("Source / Vendor")
                c_desc = st.text_input("Description")
                c_amt = st.number_input("Amount (₹)", min_value=1.0)
                if st.form_submit_button("Record Transaction"):
                    execute_db("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES (?, ?, ?, ?, ?)",
                               (str(datetime.now().date()), c_type, c_party, c_desc, c_amt))
                    st.success("Corpus record added!")

        # Admin Tab 3: Meeting Minutes
        with a_tab3:
            st.subheader("Add General Body Meeting Minutes")
            with st.form("mom_form"):
                m_title = st.text_input("Meeting Title / Purpose")
                m_att = st.text_input("Attendees (e.g., Flats 101, 102, 201)")
                m_summary = st.text_area("Key Decisions / Summary")
                if st.form_submit_button("Save Meeting MOM"):
                    execute_db("INSERT INTO meetings (date, title, attendees, summary_mom) VALUES (?, ?, ?, ?)",
                               (str(datetime.now().date()), m_title, m_att, m_summary))
                    st.success("MOM recorded successfully!")

        # Admin Tab 4: Database Export
        with a_tab4:
            st.subheader("Dump / Reuse Database File")
            with open(DB_FILE, "rb") as fp:
                st.download_button(
                    label="💾 Download SQLite Database File (.db)",
                    data=fp,
                    file_name="sri_krishna_mani.db",
                    mime="application/x-sqlite3"
                )
