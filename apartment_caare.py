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
    .alert-card { background-color: #FFF5F5; border-left: 5px solid #E53E3E; padding: 12px 18px; border-radius: 4px; margin-bottom: 12px; }
    .meeting-card { background-color: #EBF8FF; border-left: 5px solid #3182CE; padding: 12px 18px; border-radius: 4px; margin-bottom: 12px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATABASE SETUP (SQLite with Audit Logs & Reminders)
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
            months_paid TEXT,
            amount REAL,
            payment_mode TEXT,
            txn_id TEXT,
            remarks TEXT
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
            time TEXT,
            title TEXT,
            attendees TEXT,
            summary_mom TEXT,
            status TEXT -- 'Scheduled', 'Completed'
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
        cursor.execute("INSERT INTO meetings (date, time, title, attendees, summary_mom, status) VALUES ('2026-09-25', '10:00 AM', 'Annual General Body Meeting', 'All Residents', 'Discussion on festival celebrations and paint renovation.', 'Scheduled')")

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
# PAGE 1: PUBLIC DASHBOARD WITH AMC & MEETING ALERTS
# -----------------------------------------------------------------------------
if page == "📊 Public Dashboard":
    # 1. AMC Equipment Alerts
    amcs = run_query("SELECT * FROM amc_schedules")
    active_amc_alerts = []
    for _, amc in amcs.iterrows():
        due_date = datetime.strptime(amc["next_due"], "%Y-%m-%d").date()
        days_left = (due_date - datetime.now().date()).days
        if days_left <= amc["alert_days"]:
            active_amc_alerts.append(f"⚠️ **{amc['equipment']} ({amc['vendor']})** service is due in **{days_left} days** (Due: {amc['next_due']})")

    # 2. Upcoming Meeting Alerts
    upcoming_meetings = run_query("SELECT * FROM meetings WHERE status='Scheduled'")
    meeting_alerts = []
    for _, m in upcoming_meetings.iterrows():
        meeting_alerts.append(f"📅 **Upcoming Meeting:** {m['title']} | **Date:** {m['date']} at {m['time']} | **Attendees:** {m['attendees']}")

    if active_amc_alerts or meeting_alerts:
        st.subheader("🔔 Dashboard Alerts & Announcements")
        for m_alert in meeting_alerts:
            st.markdown(f"<div class='meeting-card'>{m_alert}</div>", unsafe_allow_html=True)
        for a_alert in active_amc_alerts:
            st.markdown(f"<div class='alert-card'>{a_alert}</div>", unsafe_allow_html=True)

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
    m3.metric("⚠️ Pending Dues", f"₹{pending_amount:,.0f}")
    m4.metric("🏛️ Corpus Pool", f"₹{corpus_bal:,.0f}")

    st.markdown("---")

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📋 Flat Collection Status")
        st.dataframe(f_df, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("🧾 Recent Expenses")
        exp_df = run_query("SELECT date, category, description, amount FROM expenses ORDER BY id DESC LIMIT 5")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 2: MAINTENANCE TRACKING & PAYMENTS (MULTI-MONTH SELECTION)
# -----------------------------------------------------------------------------
elif page == "💳 Maintenance Tracking & Payments":
    st.title("💳 Monthly Maintenance Portal")
    st.info(f"Current Configured Rate: **₹{monthly_fee:,.2f} / month** per flat.")

    t1, t2, t3 = st.tabs(["💳 Pay Maintenance (Multi-Month)", "📜 Payment History Log", "⚙️ Config & Rate History"])

    with t1:
        st.subheader("💳 Submit Maintenance Payment Details")
        st.caption("Select single or multiple backlog/advance months to record payment.")

        with st.form("resident_payment_form", clear_on_submit=True):
            st.markdown("#### 📌 Mandatory Information")
            c1, c2 = st.columns(2)
            
            with c1:
                selected_flat = st.selectbox(
                    "Flat Number *", 
                    ["101", "102", "201", "202", "301"],
                    index=["101", "102", "201", "202", "301"].index(current_flat) if current_flat else 0
                )
                pay_mode = st.selectbox("Payment Method *", ["UPI / QR Code", "Net Banking / NEFT", "Cheque", "Cash"])

            with c2:
                # Multi-select for backlogs / advance payments
                month_options = [
                    "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026",
                    "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026", "Dec 2026"
                ]
                selected_months = st.multiselect("Select Payment Month(s) / Backlog *", options=month_options, default=["Sep 2026"])
                
                calculated_amount = float(len(selected_months) * monthly_fee)
                paid_amount = st.number_input("Total Calculated Amount (₹) *", min_value=1.0, value=calculated_amount if calculated_amount > 0 else monthly_fee, step=100.0)

            c3, c4 = st.columns(2)
            with c3:
                payment_date = st.date_input("Date of Payment *", value=datetime.now().date())
            with c4:
                ref_id = st.text_input("Transaction ID / Reference No. *", placeholder="e.g., UPI/4261908234 or Cheque #109283")

            st.markdown("---")
            st.markdown("#### 📑 Optional Details")
            c5, c6 = st.columns(2)
            with c5:
                payer_name = st.text_input("Payer Name", placeholder="Name on UPI / Bank Account")
            with c6:
                bank_name = st.text_input("Bank / App Used", placeholder="e.g., Google Pay, PhonePe, HDFC")

            remarks = st.text_area("Additional Notes / Remarks", placeholder="e.g., Paid backlog for Aug & Sep combined.")

            submit_payment = st.form_submit_button("🚀 Submit Payment Record")

        if submit_payment:
            if not ref_id.strip():
                st.error("❌ Transaction ID / Reference No. is required.")
            elif not selected_months:
                st.error("❌ Please select at least one month for payment.")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                p_date_str = payment_date.strftime("%Y-%m-%d")
                months_str = ", ".join(selected_months)

                execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (p_date_str, selected_flat))
                execute_db("""
                    INSERT INTO payment_history (timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (now_str, selected_flat, months_str, paid_amount, f"{pay_mode} ({payer_name})" if payer_name else pay_mode, f"{ref_id} | Bank: {bank_name}" if bank_name else ref_id, remarks))

                st.success(f"✅ Payment of ₹{paid_amount} for **{months_str}** submitted for Flat {selected_flat}!")
                st.balloons()

    with t2:
        st.subheader("Historical Payment Audit Log")
        history_df = run_query("SELECT timestamp as Date, flat as 'Flat No', months_paid as 'Month(s)', amount as Amount, payment_mode as Method, txn_id as 'Txn Ref', remarks as Remarks FROM payment_history ORDER BY id DESC")
        st.dataframe(history_df, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Maintenance Rate Revision History")
        rev_df = run_query("SELECT timestamp as Date, old_amount as 'Old Rate (₹)', new_amount as 'New Rate (₹)', changed_by as 'Changed By', reason as Reason FROM maintenance_config_history ORDER BY id DESC")
        st.dataframe(rev_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 3: AI VOICE / TEXT ASSISTANT
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
                execute_db("INSERT INTO payment_history (timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks) VALUES (?, ?, 'Current Month', ?, 'Voice Assistant', 'AUTO-VOICE', '')",
                           (now_str, flat_no, monthly_fee))
                st.success(f"🤖 Flat {flat_no} marked as Paid (₹{monthly_fee}).")
            else:
                st.error("🤖 Could not find a valid flat number.")

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
# PAGE 5: AMCS & SCHEDULES
# -----------------------------------------------------------------------------
elif page == "📅 AMCs & Schedules":
    st.title("📅 Equipment Maintenance & AMC Schedules")
    amc_df = run_query("SELECT id, equipment as Equipment, vendor as Vendor, next_due as 'Next Service Due', alert_days as 'Alert Lead Days' FROM amc_schedules")
    st.dataframe(amc_df, use_container_width=True, hide_index=True)

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
# PAGE 7: MEETINGS & MINUTES (MOM) WITH ALERTS
# -----------------------------------------------------------------------------
elif page == "📝 Meetings & Minutes (MOM)":
    st.title("📝 Society Meetings & Minutes")
    
    st.subheader("📅 Scheduled Upcoming Meetings")
    sched_df = run_query("SELECT date as Date, time as Time, title as Title, attendees as Attendees, status as Status FROM meetings WHERE status='Scheduled'")
    st.dataframe(sched_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📜 Past Meeting Minutes (MOM)")
    mom_df = run_query("SELECT date as Date, title as Title, attendees as Attendees, summary_mom as Minutes FROM meetings WHERE status='Completed' OR summary_mom != '' ORDER BY id DESC")
    st.dataframe(mom_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 8: ADMIN CONTROL PANEL (AMC & MEETING ALERT MANAGEMENT)
# -----------------------------------------------------------------------------
elif page == "⚙️ Admin Control Panel":
    st.title("⚙️ Admin Control Panel")
    if not st.session_state.admin_logged_in:
        st.warning("🔒 Admin Passcode Required.")
    else:
        a1, a2, a3, a4, a5, a6 = st.tabs([
            "⚙️ Fee Rate", 
            "🛠️ Manage AMCs", 
            "📅 Schedule Meetings", 
            "Approvals", 
            "Corpus Ops", 
            "Database Export"
        ])

        # Tab 1: Configure Fee
        with a1:
            st.subheader("Configure Maintenance Fee")
            with st.form("config_fee_form"):
                new_rate = st.number_input("New Monthly Rate (₹)", min_value=0.0, value=monthly_fee, step=100.0)
                revision_reason = st.text_area("Reason for Rate Revision")
                if st.form_submit_button("Update Rate"):
                    if new_rate != monthly_fee:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        execute_db("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', ?)", (str(new_rate),))
                        execute_db("INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason) VALUES (?, ?, ?, ?, ?)",
                                   (now_str, monthly_fee, new_rate, "Admin", revision_reason))
                        st.success(f"Rate updated to ₹{new_rate}!")
                        st.rerun()

        # Tab 2: Admin AMC & Equipment Management
        with a2:
            st.subheader("🛠️ Add or Update Equipment AMC")
            with st.form("add_amc_form"):
                eq_name = st.text_input("Equipment / Service Name", placeholder="e.g. Generator Service")
                eq_vendor = st.text_input("Vendor Name", placeholder="e.g. Kirloskar Care")
                eq_next_due = st.date_input("Next Service Due Date")
                eq_alert_days = st.number_input("Alert Lead Days (Trigger alert X days prior)", min_value=1, value=15)
                
                if st.form_submit_button("Save AMC Contract"):
                    execute_db("INSERT INTO amc_schedules (equipment, vendor, next_due, alert_days) VALUES (?, ?, ?, ?)",
                               (eq_name, eq_vendor, str(eq_next_due), eq_alert_days))
                    st.success("AMC Schedule updated!")
                    st.rerun()

            st.markdown("---")
            st.write("**Existing AMC Contracts (Delete Option):**")
            existing_amcs = run_query("SELECT * FROM amc_schedules")
            for _, amc_item in existing_amcs.iterrows():
                col_info, col_del = st.columns([4, 1])
                col_info.write(f"• **{amc_item['equipment']}** ({amc_item['vendor']}) — Next Due: {amc_item['next_due']}")
                if col_del.button("Delete", key=f"del_amc_{amc_item['id']}"):
                    execute_db("DELETE FROM amc_schedules WHERE id=?", (amc_item['id'],))
                    st.success("Deleted!")
                    st.rerun()

        # Tab 3: Schedule Meetings & Send Alerts
        with a3:
            st.subheader("📢 Schedule Meeting & Broadcast Alert")
            with st.form("schedule_meeting_form"):
                m_date = st.date_input("Meeting Date")
                m_time = st.text_input("Meeting Time", placeholder="e.g. 10:30 AM")
                m_title = st.text_input("Meeting Title / Agenda")
                m_attendees = st.text_input("Target Attendees", value="All Flat Owners")
                
                if st.form_submit_button("Schedule & Broadcast Alert"):
                    execute_db("INSERT INTO meetings (date, time, title, attendees, summary_mom, status) VALUES (?, ?, ?, ?, '', 'Scheduled')",
                               (str(m_date), m_time, m_title, m_attendees))
                    st.success("Meeting Scheduled! Alert broadcasted to Dashboard.")
                    st.rerun()

            st.markdown("---")
            st.subheader("📝 Complete Meeting & Save MOM")
            scheduled_meetings = run_query("SELECT * FROM meetings WHERE status='Scheduled'")
            if not scheduled_meetings.empty:
                for _, sm in scheduled_meetings.iterrows():
                    st.write(f"**{sm['title']}** on {sm['date']} at {sm['time']}")
                    with st.form(f"mom_form_{sm['id']}"):
                        mom_text = st.text_area("Minutes of Meeting (MOM)")
                        if st.form_submit_button("Mark Completed & Save MOM"):
                            execute_db("UPDATE meetings SET summary_mom=?, status='Completed' WHERE id=?", (mom_text, sm['id']))
                            st.success("MOM Saved and Meeting Archived!")
                            st.rerun()

        # Tab 4: Approvals
        with a4:
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

        # Tab 5: Corpus Ops
        with a5:
            with st.form("corpus_form"):
                c_type = st.selectbox("Type", ["Contribution", "Expenditure"])
                c_party = st.text_input("Source/Vendor")
                c_desc = st.text_input("Description")
                c_amt = st.number_input("Amount (₹)", min_value=1.0)
                if st.form_submit_button("Record Entry"):
                    execute_db("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES (?, ?, ?, ?, ?)",
                               (str(datetime.now().date()), c_type, c_party, c_desc, c_amt))
                    st.success("Corpus updated!")

        # Tab 6: Export
        with a6:
            with open(DB_FILE, "rb") as fp:
                st.download_button("💾 Download SQLite Database (.db)", fp, file_name="sri_krishna_mani.db", mime="application/x-sqlite3")
