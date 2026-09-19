import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# =============================================================================
# 1. DATABASE CONFIGURATION & PERSISTENCE
# =============================================================================
DB_FILE = "sri_krishna_mani.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def run_query(query, params=()):
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute_db(query, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users Table for Login & RBAC
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            flat TEXT
        )
    """)

    # Flats Master
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat TEXT PRIMARY KEY,
            owner_name TEXT,
            contact TEXT,
            status TEXT DEFAULT 'Pending',
            last_paid TEXT DEFAULT '-'
        )
    """)
    
    # Global Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Rate Revision History
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

    # Payment Records
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

    # Operating Expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL,
            approved_by TEXT
        )
    """)

    # Corpus / Sinking Fund
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

    # AMC & Vendor Contracts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS amc_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment TEXT,
            vendor TEXT,
            contact_person TEXT,
            next_due TEXT,
            cost REAL,
            alert_days INTEGER DEFAULT 30
        )
    """)

    # Helpdesk / Complaints
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            flat TEXT,
            category TEXT,
            issue TEXT,
            status TEXT DEFAULT 'Open',
            resolution_notes TEXT DEFAULT ''
        )
    """)

    # Meetings & MoM
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            title TEXT,
            attendees TEXT,
            summary_mom TEXT,
            status TEXT DEFAULT 'Scheduled'
        )
    """)

    # Migrations Safety Guard
    migrations = [
        ("payment_history", "months_paid", "TEXT DEFAULT 'Current Month'"),
        ("payment_history", "remarks", "TEXT DEFAULT ''"),
        ("meetings", "time", "TEXT DEFAULT '10:00 AM'"),
        ("meetings", "status", "TEXT DEFAULT 'Scheduled'"),
        ("issues", "resolution_notes", "TEXT DEFAULT ''")
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Initial Seed Data Creation
    cursor.execute("SELECT COUNT(*) FROM flats")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO flats VALUES (?, ?, ?, ?, ?)", [
            ("101", "R. Sharma", "+91 9876543210", "Paid", "2026-09-01"),
            ("102", "A. Verma", "+91 9876543211", "Pending", "-"),
            ("201", "K. Rao", "+91 9876543212", "Paid", "2026-09-03"),
            ("202", "S. Gupta", "+91 9876543213", "Pending", "-"),
            ("301", "M. Patel", "+91 9876543214", "Paid", "2026-09-05"),
        ])
        cursor.execute("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', '2000')")
        cursor.execute("""
            INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason) 
            VALUES (?, ?, ?, ?, ?)
        """, (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 0, 2000, "System Admin", "Initial Standard Rate"))
        
        cursor.executemany("INSERT INTO amc_schedules (equipment, vendor, contact_person, next_due, cost, alert_days) VALUES (?, ?, ?, ?, ?, ?)", [
            ("Lift / Elevator", "Otis Elevators", "Ramesh (9811002233)", "2026-09-28", 12000.0, 15),
            ("Water Softener Plant", "AquaTech Systems", "Suresh (9811002244)", "2026-10-15", 4500.0, 30),
            ("Diesel Generator (DG)", "Cummins Power", "Vikas (9811002255)", "2026-11-01", 8500.0, 30)
        ])
        
        cursor.execute("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES ('2026-01-01', 'Contribution', 'All Flats', 'Initial Sinking Fund Deposit', 250000)")
        cursor.execute("INSERT INTO meetings (date, time, title, attendees, summary_mom, status) VALUES ('2026-09-25', '10:00 AM', 'Annual General Meeting', 'All Flat Owners', 'Festival budget & Painting discussion.', 'Scheduled')")

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", [
            ("admin", "admin123", "Admin", ""),
            ("101", "pass101", "Resident", "101"),
            ("102", "pass102", "Resident", "102"),
            ("201", "pass201", "Resident", "201"),
            ("202", "pass202", "Resident", "202"),
            ("301", "pass301", "Resident", "301"),
        ])

    conn.commit()
    conn.close()

# Initialize DB
init_db()

# =============================================================================
# 2. HELPER FUNCTIONS
# =============================================================================
def get_month_str(date_obj):
    return date_obj.strftime("%b %Y")

def get_next_month_str(date_obj):
    year = date_obj.year + (1 if date_obj.month == 12 else 0)
    month = 1 if date_obj.month == 12 else date_obj.month + 1
    return datetime(year, month, 1).strftime("%b %Y")

def get_monthly_fee():
    df = run_query("SELECT value FROM settings WHERE key='monthly_maintenance'")
    if not df.empty:
        try:
            return float(df.iloc[0]['value'])
        except ValueError:
            return 2000.0
    return 2000.0

# =============================================================================
# 3. STREAMLIT UI CONFIG & LOGIN SYSTEM
# =============================================================================
st.set_page_config(
    page_title="Sri Krishna Mani Apartments Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_role"] = ""
    st.session_state["user_flat"] = ""

# -----------------------------------------------------------------------------
# LOGIN SCREEN
# -----------------------------------------------------------------------------
if not st.session_state["logged_in"]:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.title("🏢 Sri Krishna Mani Apartments")
        st.subheader("🔑 Resident & Admin Login Portal")
        
        with st.form("login_form"):
            user_input = st.text_input("Username / Flat Number (e.g., admin, 101, 201)")
            pass_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("🚀 Log In")

            if submit_login:
                user_res = run_query("SELECT * FROM users WHERE username=? AND password=?", (user_input.strip(), pass_input.strip()))
                if not user_res.empty:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_res.iloc[0]["username"]
                    st.session_state["user_role"] = user_res.iloc[0]["role"]
                    st.session_state["user_flat"] = user_res.iloc[0]["flat"]
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Username or Password.")

        st.info("""
        **Default Demo Credentials:**
        * **Admin:** Username `admin` | Password `admin123`
        * **Flat Owners:** Username `101` (Pass: `pass101`), Username `201` (Pass: `pass201`)
        """)
    st.stop()

# =============================================================================
# 4. LOGGED-IN NAVIGATION & SIDEBAR
# =============================================================================
monthly_fee = get_monthly_fee()
is_admin = st.session_state["user_role"] == "Admin"

st.sidebar.title("🏢 Housing Portal")
st.sidebar.write(f"Logged in as: **{st.session_state['username']}**")
st.sidebar.caption(f"Role: **{st.session_state['user_role']}**" + (f" (Flat {st.session_state['user_flat']})" if st.session_state['user_flat'] else ""))

if st.sidebar.button("🚪 Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["user_role"] = ""
    st.session_state["user_flat"] = ""
    st.rerun()

st.sidebar.markdown("---")

# Shared Navigation for Transparency
navigation_options = [
    "📊 Society Dashboard & Corpus",
    "💳 Maintenance & Payments",
    "💸 Financial Ledger & Expenses",
    "🛠️ AMC & Vendor Contracts",
    "🚨 Helpdesk & Complaints",
    "📅 Meetings & MoM Logs"
]

if is_admin:
    navigation_options.append("⚙️ Admin Settings")

page = st.sidebar.radio("Navigation Menu", navigation_options)

# =============================================================================
# PAGE: SOCIETY DASHBOARD & CORPUS (COMMON VIEW)
# =============================================================================
if page == "📊 Society Dashboard & Corpus":
    st.title("📊 Society Dashboard & Corpus Overview")
    st.caption(f"Real-time operational summary for {datetime.now().strftime('%B %Y')}")

    flats_df = run_query("SELECT * FROM flats")
    expenses_df = run_query("SELECT SUM(amount) as total FROM expenses")
    corpus_df = run_query("SELECT SUM(amount) as total FROM corpus WHERE type='Contribution'")
    pending_tickets = run_query("SELECT COUNT(*) as cnt FROM issues WHERE status != 'Resolved'").iloc[0]['cnt']

    total_flats = len(flats_df)
    paid_flats = len(flats_df[flats_df["status"] == "Paid"]) if not flats_df.empty else 0
    total_expenses = expenses_df.iloc[0]["total"] if not expenses_df.empty and expenses_df.iloc[0]["total"] else 0.0
    total_corpus = corpus_df.iloc[0]["total"] if not corpus_df.empty and corpus_df.iloc[0]["total"] else 0.0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Current Cycle Paid", f"{paid_flats} / {total_flats} Flats", delta=f"{int((paid_flats/total_flats)*100 if total_flats else 0)}% Paid")
    kpi2.metric("Total Expenses Logged", f"₹{total_expenses:,.2f}")
    kpi3.metric("Corpus / Sinking Balance", f"₹{total_corpus:,.2f}")
    kpi4.metric("Open Helpdesk Tickets", f"{pending_tickets} Pending", delta_color="inverse")

    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("🏠 Flat Maintenance Collection Status")
        st.dataframe(flats_df, hide_index=True, use_container_width=True)

    with col_right:
        st.subheader("⚠️ Action Reminders & Alerts")
        amc_alert_df = run_query("SELECT equipment, next_due, vendor FROM amc_schedules ORDER BY next_due ASC LIMIT 3")
        if not amc_alert_df.empty:
            for _, row in amc_alert_df.iterrows():
                st.warning(f"🔧 **{row['equipment']}** due `{row['next_due']}`")

        open_issues = run_query("SELECT flat, category, issue FROM issues WHERE status='Open' LIMIT 3")
        if not open_issues.empty:
            for _, row in open_issues.iterrows():
                st.error(f"🚨 **Flat {row['flat']}**: {row['issue'][:35]}...")

# =============================================================================
# PAGE: MAINTENANCE & PAYMENTS
# =============================================================================
elif page == "💳 Maintenance & Payments":
    st.title("💳 Maintenance & Payment Portal")

    if not is_admin:
        st.info(f"Viewing payment portal for **Flat {st.session_state['user_flat']}**. Standard Maintenance Rate: **₹{monthly_fee:,.2f} / month**.")

    t1, t2 = st.tabs(["💳 Record Payment", "📜 Payment History Log"])

    # TAB 1: RECORD PAYMENT
    with t1:
        st.subheader("💳 Submit Maintenance Payment")

        flats_df = run_query("SELECT flat FROM flats ORDER BY flat")
        flat_list = flats_df["flat"].tolist() if not flats_df.empty else ["101", "102", "201", "202", "301"]

        if is_admin:
            selected_flat = st.selectbox("Select Flat Number *", flat_list)
        else:
            selected_flat = st.session_state["user_flat"]
            st.text_input("Flat Number", value=f"Flat {selected_flat}", disabled=True)

        now = datetime.now()
        current_month_str = get_month_str(now)
        next_month_str = get_next_month_str(now)

        paid_records = run_query("SELECT months_paid FROM payment_history WHERE flat=?", (selected_flat,))
        is_current_month_paid = False
        
        if not paid_records.empty:
            for _, row in paid_records.iterrows():
                paid_months = [m.strip() for m in str(row['months_paid']).split(',')]
                if current_month_str in paid_months:
                    is_current_month_paid = True
                    break

        if is_current_month_paid:
            st.success(f"✅ **Flat {selected_flat} HAS PAID for current month ({current_month_str}).** Defaulting dropdown to next month.")
            default_selected_months = [next_month_str]
        else:
            st.warning(f"⚠️ **Flat {selected_flat} HAS NOT PAID for current month ({current_month_str}).**")
            default_selected_months = [current_month_str]

        month_options = [
            "Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026",
            "Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026", "Dec 2026",
            "Jan 2027", "Feb 2027", "Mar 2027"
        ]

        st.markdown("---")

        with st.form("resident_payment_form", clear_on_submit=False):
            st.markdown("#### 📌 Mandatory Payment Information")
            
            c1, c2 = st.columns(2)
            with c1:
                pay_mode = st.selectbox("Payment Method *", ["UPI / QR Code", "Net Banking / NEFT", "Cheque", "Cash"])
                payment_date = st.date_input("Date of Payment *", value=now.date())

            with c2:
                selected_months = st.multiselect("Select Payment Month(s) *", options=month_options, default=default_selected_months)
                calculated_amount = float(len(selected_months) * monthly_fee)
                paid_amount = st.number_input("Total Amount Paid (₹) *", min_value=1.0, value=calculated_amount if calculated_amount > 0 else float(monthly_fee), step=100.0)

            ref_id = st.text_input("Transaction ID / Reference No. *", placeholder="e.g., UPI/4261908234 or Cheque #109283")

            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                payer_name = st.text_input("Payer Name", placeholder="Name on account/UPI")
            with c4:
                bank_name = st.text_input("Bank / Payment App", placeholder="e.g., Google Pay, HDFC")

            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Advance payment.")

            st.markdown("---")
            allow_duplicate = st.checkbox("⚠️ Force Submission / Allow Duplicate Entry")

            submit_payment = st.form_submit_button("🚀 Submit Payment")

        if submit_payment:
            if not ref_id.strip():
                st.error("❌ Transaction ID / Reference No. is required.")
            elif not selected_months:
                st.error("❌ Please select at least one month.")
            else:
                existing_records = run_query("SELECT timestamp, months_paid, txn_id FROM payment_history WHERE flat=?", (selected_flat,))
                duplicate_found = False
                conflicting_months = []

                if not existing_records.empty:
                    for _, row in existing_records.iterrows():
                        past_months = [m.strip() for m in str(row['months_paid']).split(',')]
                        for m in selected_months:
                            if m in past_months:
                                duplicate_found = True
                                conflicting_months.append(f"{m} (Logged: {row['timestamp']} | Ref: {row['txn_id']})")

                if duplicate_found and not allow_duplicate:
                    st.error(f"🚨 **Duplicate Payment Warning for Flat {selected_flat}!**")
                    st.warning("The selected month(s) are already logged as paid:")
                    for dup in set(conflicting_months):
                        st.write(f"• **{dup}**")
                    st.info("💡 To override and allow duplicate entry, check **'⚠️ Force Submission / Allow Duplicate Entry'** and click Submit again.")
                else:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p_date_str = payment_date.strftime("%Y-%m-%d")
                    months_str = ", ".join(selected_months)

                    execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (p_date_str, selected_flat))
                    
                    execute_db("""
                        INSERT INTO payment_history (timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now_str, 
                        selected_flat, 
                        months_str, 
                        paid_amount, 
                        f"{pay_mode} ({payer_name})" if payer_name else pay_mode, 
                        f"{ref_id} | {bank_name}" if bank_name else ref_id, 
                        f"[OVERRIDE DUPLICATE] {remarks}" if duplicate_found else remarks
                    ))

                    st.success(f"✅ Payment of ₹{paid_amount:,.2f} recorded for **Flat {selected_flat}** ({months_str})!")
                    st.balloons()
                    st.rerun()

    # TAB 2: PAYMENT HISTORY LOG
    with t2:
        st.subheader("📜 Payment History Log")
        
        if is_admin:
            history_df = run_query("SELECT id, timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks FROM payment_history ORDER BY id DESC")
        else:
            history_df = run_query("SELECT id, timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks FROM payment_history WHERE flat=? ORDER BY id DESC", (st.session_state["user_flat"],))

        if history_df.empty:
            st.info("No payment history records found.")
        else:
            if is_admin:
                flat_filter = st.selectbox("Filter Flat", ["All"] + flat_list)
                if flat_filter != "All":
                    history_df = history_df[history_df["flat"] == flat_filter]

            st.dataframe(
                history_df,
                column_config={
                    "id": "ID",
                    "timestamp": "Timestamp",
                    "flat": "Flat",
                    "months_paid": "Month(s) Covered",
                    "amount": st.column_config.NumberColumn("Amount Paid", format="₹%.2f"),
                    "payment_mode": "Method",
                    "txn_id": "Reference ID",
                    "remarks": "Notes"
                },
                hide_index=True,
                use_container_width=True
            )

# =============================================================================
# PAGE: FINANCIAL LEDGER & EXPENSES (COMMON VIEW)
# =============================================================================
elif page == "💸 Financial Ledger & Expenses":
    st.title("💸 Financial Operations & Society Ledger")

    e1, e2 = st.tabs(["🧾 Daily Operating Expenses", "🏦 Corpus Fund Ledger"])

    with e1:
        st.subheader("Daily Operating Expenses")
        
        if is_admin:
            with st.expander("➕ Log New Maintenance Expense", expanded=True):
                with st.form("expense_form"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        exp_date = st.date_input("Expense Date", datetime.now().date())
                        cat = st.selectbox("Category", ["Electricity Bill", "Water Tankers", "Security Salary", "Cleaning Supplies", "Lift Servicing", "Misc"])
                    with c2:
                        amt = st.number_input("Amount (₹) *", min_value=1.0, step=100.0)
                        approved_by = st.text_input("Approved By", value="President/Treasurer")
                    with c3:
                        desc = st.text_area("Vendor / Description *")
                    
                    sub_exp = st.form_submit_button("Log Operating Expense")

                if sub_exp:
                    if not desc.strip():
                        st.error("Please add a description.")
                    else:
                        execute_db("INSERT INTO expenses (date, category, description, amount, approved_by) VALUES (?, ?, ?, ?, ?)",
                                   (exp_date.strftime("%Y-%m-%d"), cat, desc, amt, approved_by))
                        st.success("Expense logged!")
                        st.rerun()

        exp_df = run_query("SELECT id, date, category, description, amount, approved_by FROM expenses ORDER BY id DESC")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

    with e2:
        st.subheader("Corpus Fund Ledger (Sinking Fund)")
        
        if is_admin:
            with st.expander("➕ Add Corpus Entry"):
                with st.form("corpus_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        c_date = st.date_input("Date", datetime.now().date())
                        c_type = st.selectbox("Entry Type", ["Contribution", "Withdrawal"])
                        c_source = st.text_input("Source / Flat / Vendor", value="All Flats")
                    with c2:
                        c_amt = st.number_input("Amount (₹)", min_value=1.0, step=500.0)
                        c_desc = st.text_area("Purpose / Description")
                    
                    sub_corp = st.form_submit_button("Save Corpus Record")

                if sub_corp:
                    execute_db("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES (?, ?, ?, ?, ?)",
                               (c_date.strftime("%Y-%m-%d"), c_type, c_source, c_desc, c_amt))
                    st.success("Corpus record saved!")
                    st.rerun()

        corpus_df = run_query("SELECT * FROM corpus ORDER BY id DESC")
        st.dataframe(corpus_df, use_container_width=True, hide_index=True)

# =============================================================================
# PAGE: AMC & VENDOR CONTRACTS (COMMON VIEW)
# =============================================================================
elif page == "🛠️ AMC & Vendor Contracts":
    st.title("🛠️ Vendor Contracts & AMC Tracker")
    st.caption("Public schedule of maintenance service contracts for society equipment.")

    if is_admin:
        with st.expander("➕ Add New Vendor / AMC Contract"):
            with st.form("amc_form"):
                c1, c2 = st.columns(2)
                with c1:
                    eq_name = st.text_input("Equipment Name *", placeholder="e.g., CCTV System")
                    v_name = st.text_input("Vendor Company *", placeholder="e.g., SecureEye Pvt Ltd")
                    c_person = st.text_input("Contact Person & Number *")
                with c2:
                    due_date = st.date_input("Next Service / Renewal Due *")
                    cost_amt = st.number_input("Contract Cost (₹)", min_value=0.0, step=500.0)
                    a_days = st.number_input("Alert Lead Time (Days)", min_value=1, value=30)

                sub_amc = st.form_submit_button("Add AMC Contract")

            if sub_amc:
                if not eq_name or not v_name:
                    st.error("Please fill in mandatory fields.")
                else:
                    execute_db("INSERT INTO amc_schedules (equipment, vendor, contact_person, next_due, cost, alert_days) VALUES (?, ?, ?, ?, ?, ?)",
                               (eq_name, v_name, c_person, due_date.strftime("%Y-%m-%d"), cost_amt, a_days))
                    st.success("AMC contract added!")
                    st.rerun()

    amc_df = run_query("SELECT * FROM amc_schedules ORDER BY next_due ASC")
    st.dataframe(amc_df, use_container_width=True, hide_index=True)

# =============================================================================
# PAGE: HELPDESK & COMPLAINTS (COMMON VIEW WITH MY-FLAT FILTER)
# =============================================================================
elif page == "🚨 Helpdesk & Complaints":
    st.title("🚨 Resident Complaints & Helpdesk")

    t1, t2 = st.tabs(["➕ Raise Ticket", "🛠️ View All Complaints"])

    with t1:
        st.subheader("Submit Maintenance Request")
        with st.form("new_ticket_form"):
            if is_admin:
                flat_no = st.selectbox("Flat Number", run_query("SELECT flat FROM flats")["flat"].tolist())
            else:
                flat_no = st.session_state["user_flat"]
                st.text_input("Flat Number", value=f"Flat {flat_no}", disabled=True)

            cat = st.selectbox("Category", ["Plumbing", "Electrical", "Lift/Elevator", "Water Supply", "Security", "Cleanliness", "Other"])
            issue_text = st.text_area("Issue Description *", placeholder="Describe the issue in detail...")
            sub_ticket = st.form_submit_button("Submit Helpdesk Ticket")

        if sub_ticket:
            if not issue_text.strip():
                st.error("Please enter details of the issue.")
            else:
                execute_db("INSERT INTO issues (date, flat, category, issue, status) VALUES (?, ?, ?, ?, 'Open')",
                           (datetime.now().strftime("%Y-%m-%d"), flat_no, cat, issue_text))
                st.success("Ticket submitted successfully!")
                st.rerun()

    with t2:
        st.subheader("Society Complaints Log")
        
        # Filtering for Residents so they can check common issues or filter by their flat
        if not is_admin:
            filter_mode = st.radio("View Filter:", ["All Society Issues (Common View)", f"Only My Flat ({st.session_state['user_flat']})"], horizontal=True)
            if "Only My Flat" in filter_mode:
                issues_df = run_query("SELECT * FROM issues WHERE flat=? ORDER BY id DESC", (st.session_state["user_flat"],))
            else:
                issues_df = run_query("SELECT * FROM issues ORDER BY id DESC")
        else:
            issues_df = run_query("SELECT * FROM issues ORDER BY id DESC")

        if issues_df.empty:
            st.info("No tickets recorded.")
        else:
            for _, row in issues_df.iterrows():
                status_color = "🔴" if row['status'] == "Open" else "🟡" if row['status'] == "In Progress" else "🟢"
                with st.expander(f"{status_color} Ticket #{row['id']} - Flat {row['flat']} ({row['category']}) | Status: {row['status']}"):
                    st.write(f"**Date Logged:** {row['date']}")
                    st.write(f"**Description:** {row['issue']}")
                    st.write(f"**Resolution Notes:** {row['resolution_notes'] if row['resolution_notes'] else 'Pending resolution notes.'}")
                    
                    if is_admin:
                        st.markdown("---")
                        st.markdown("##### 🛠️ Admin Status Management")
                        with st.form(f"update_ticket_{row['id']}"):
                            new_status = st.selectbox("Status", ["Open", "In Progress", "Resolved"], index=["Open", "In Progress", "Resolved"].index(row['status']))
                            res_notes = st.text_area("Resolution Remarks", value=row['resolution_notes'])
                            update_sub = st.form_submit_button("Update Ticket")

                        if update_sub:
                            execute_db("UPDATE issues SET status=?, resolution_notes=? WHERE id=?", (new_status, res_notes, row['id']))
                            st.success("Ticket updated!")
                            st.rerun()

# =============================================================================
# PAGE: MEETINGS & MOM LOGS (SHARED)
# =============================================================================
elif page == "📅 Meetings & MoM Logs":
    st.title("📅 General Body Meetings & Minutes")
    
    if is_admin:
        with st.expander("➕ Schedule New Meeting / Log MoM"):
            with st.form("meeting_form"):
                c1, c2 = st.columns(2)
                with c1:
                    m_date = st.date_input("Date")
                    m_time = st.text_input("Time", value="10:00 AM")
                    m_title = st.text_input("Meeting Title *")
                with c2:
                    m_attendees = st.text_input("Attendees", value="All Flat Owners")
                    m_status = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])
                
                m_mom = st.text_area("Summary / Minutes of Meeting (MoM)")
                sub_m = st.form_submit_button("Save Meeting")

            if sub_m:
                execute_db("INSERT INTO meetings (date, time, title, attendees, summary_mom, status) VALUES (?, ?, ?, ?, ?, ?)",
                           (m_date.strftime("%Y-%m-%d"), m_time, m_title, m_attendees, m_mom, m_status))
                st.success("Meeting saved!")
                st.rerun()

    meetings_df = run_query("SELECT * FROM meetings ORDER BY id DESC")
    st.dataframe(meetings_df, use_container_width=True, hide_index=True)

# =============================================================================
# PAGE: ADMIN SETTINGS (ADMIN ONLY)
# =============================================================================
elif page == "⚙️ Admin Settings":
    st.title("⚙️ System Administration & User Accounts")

    t1, t2, t3 = st.tabs(["⚙️ Configure Maintenance Fee", "🏠 Manage Flats", "🔑 Manage User Logins"])

    with t1:
        st.subheader("Configure Default Maintenance Fee")
        with st.form("rate_config_form"):
            new_rate = st.number_input("New Default Rate (₹)", min_value=100.0, value=float(monthly_fee), step=100.0)
            changed_by = st.text_input("Authorizing Person", value="Admin")
            reason = st.text_area("Reason for Tariff Revision")
            submit_rate = st.form_submit_button("Update Standard Rate")

        if submit_rate:
            if new_rate != monthly_fee:
                execute_db("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', ?)", (str(new_rate),))
                execute_db("""
                    INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monthly_fee, new_rate, changed_by, reason))
                st.success("Standard fee updated!")
                st.rerun()

    with t2:
        st.subheader("Flats Master List")
        st.dataframe(run_query("SELECT * FROM flats ORDER BY flat"), use_container_width=True, hide_index=True)

    with t3:
        st.subheader("User Passwords & Roles")
        users_df = run_query("SELECT username, role, flat FROM users")
        st.dataframe(users_df, use_container_width=True, hide_index=True)

        with st.expander("➕ Add / Reset User Password"):
            with st.form("user_pwd_form"):
                u_name = st.text_input("Username / Flat")
                u_pass = st.text_input("Password")
                u_role = st.selectbox("Role", ["Resident", "Admin"])
                u_flat = st.text_input("Associated Flat No (Leave blank for Admin)")
                sub_u = st.form_submit_button("Save User Credentials")

            if sub_u:
                execute_db("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (u_name, u_pass, u_role, u_flat))
                st.success("User credentials saved!")
                st.rerun()
