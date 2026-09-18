import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# DATABASE SETUP & HELPERS
# -----------------------------------------------------------------------------
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
    
    # Base Tables Creation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flats (
            flat TEXT PRIMARY KEY,
            owner_name TEXT,
            status TEXT,
            last_paid TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS amc_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment TEXT,
            vendor TEXT,
            next_due TEXT,
            alert_days INTEGER
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            title TEXT,
            attendees TEXT,
            summary_mom TEXT,
            status TEXT
        )
    """)

    # Safety Column Migrations for Schema Upgrades
    migrations = [
        ("payment_history", "months_paid", "TEXT DEFAULT 'Current Month'"),
        ("payment_history", "remarks", "TEXT DEFAULT ''"),
        ("meetings", "time", "TEXT DEFAULT '10:00 AM'"),
        ("meetings", "status", "TEXT DEFAULT 'Scheduled'")
    ]

    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Default Seed Data for Initial Run
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
        cursor.execute("""
            INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason) 
            VALUES (?, ?, ?, ?, ?)
        """, (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 0, 2000, "System Admin", "Initial Maintenance Rate Set"))
        
        cursor.executemany("INSERT INTO amc_schedules (equipment, vendor, next_due, alert_days) VALUES (?, ?, ?, ?)", [
            ("Water Softener System", "Zero B Care", "2026-10-15", 30),
            ("Lift / Elevator", "Otis India", "2026-09-25", 10),
            ("Water Tank Cleaning", "CleanAqua", "2026-09-22", 7)
        ])
        cursor.execute("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES ('2026-01-01', 'Contribution', 'All Flats', 'Initial Corpus Pool', 150000)")
        cursor.execute("INSERT INTO meetings (date, time, title, attendees, summary_mom, status) VALUES ('2026-09-25', '10:00 AM', 'Annual General Body Meeting', 'All Residents', 'Discussion on festival celebrations.', 'Scheduled')")

    conn.commit()
    conn.close()

# Initialize Database
init_db()

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & NAVIGATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sri Krishna Mani Apartment Management",
    page_icon="🏢",
    layout="wide"
)

monthly_fee = get_monthly_fee()

st.sidebar.title("🏢 Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "📊 Dashboard & Overview",
        "💳 Maintenance Tracking & Payments",
        "💸 Expense & Corpus Management",
        "🛠️ AMC & Vendor Management",
        "🚨 Complaints & Helpdesk",
        "📅 Meetings & MoM Log"
    ]
)

current_flat = st.sidebar.selectbox("Simulate Flat Context (Optional)", ["", "101", "102", "201", "202", "301"])

# -----------------------------------------------------------------------------
# PAGE 1: DASHBOARD & OVERVIEW
# -----------------------------------------------------------------------------
if page == "📊 Dashboard & Overview":
    st.title("📊 Apartment Management Overview")
    st.caption("Sri Krishna Mani Apartments Housing Portal")

    flats_df = run_query("SELECT * FROM flats")
    expenses_df = run_query("SELECT SUM(amount) as total FROM expenses")
    corpus_df = run_query("SELECT SUM(amount) as total FROM corpus WHERE type='Contribution'")
    
    total_flats = len(flats_df)
    paid_flats = len(flats_df[flats_df["status"] == "Paid"]) if not flats_df.empty else 0
    total_expenses = expenses_df.iloc[0]["total"] if not expenses_df.empty and expenses_df.iloc[0]["total"] else 0.0
    total_corpus = corpus_df.iloc[0]["total"] if not corpus_df.empty and corpus_df.iloc[0]["total"] else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Flats", total_flats)
    m2.metric("Paid (Current Cycle)", f"{paid_flats} / {total_flats}")
    m3.metric("Total Expenses Logged", f"₹{total_expenses:,.2f}")
    m4.metric("Corpus Fund Balance", f"₹{total_corpus:,.2f}")

    st.markdown("---")
    st.subheader("🏠 Flat Maintenance Status Overview")
    st.dataframe(flats_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 2: MAINTENANCE TRACKING & PAYMENTS
# -----------------------------------------------------------------------------
elif page == "💳 Maintenance Tracking & Payments":
    st.title("💳 Monthly Maintenance Portal")
    st.info(f"Current Configured Rate: **₹{monthly_fee:,.2f} / month** per flat.")

    t1, t2, t3 = st.tabs(["💳 Pay Maintenance", "📜 Payment History Log", "⚙️ Config & Rate History"])

    # -------------------------------------------------------------------------
    # TAB 1: PAY MAINTENANCE
    # -------------------------------------------------------------------------
    with t1:
        st.subheader("💳 Submit Maintenance Payment Details")

        flats_df = run_query("SELECT flat FROM flats ORDER BY flat")
        flat_list = flats_df["flat"].tolist() if not flats_df.empty else ["101", "102", "201", "202", "301"]
        
        selected_flat = st.selectbox(
            "Select Flat Number *", 
            flat_list,
            index=flat_list.index(current_flat) if (current_flat and current_flat in flat_list) else 0
        )

        now = datetime.now()
        current_month_str = get_month_str(now)
        next_month_str = get_next_month_str(now)

        paid_records = run_query(
            "SELECT months_paid, timestamp, amount FROM payment_history WHERE flat=?", 
            (selected_flat,)
        )

        is_current_month_paid = False
        if not paid_records.empty:
            for _, row in paid_records.iterrows():
                paid_months = [m.strip() for m in str(row['months_paid']).split(',')]
                if current_month_str in paid_months:
                    is_current_month_paid = True
                    break

        if is_current_month_paid:
            st.success(f"✅ **Flat {selected_flat} HAS ALREADY PAID for the current month ({current_month_str}).**")
            default_selected_months = [next_month_str]
        else:
            st.warning(f"⚠️ **Flat {selected_flat} HAS NOT PAID for the current month ({current_month_str}).**")
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
                selected_months = st.multiselect(
                    "Select Payment Month(s) *", 
                    options=month_options, 
                    default=default_selected_months
                )
                calculated_amount = float(len(selected_months) * monthly_fee)
                paid_amount = st.number_input(
                    "Total Amount Paid (₹) *", 
                    min_value=1.0, 
                    value=calculated_amount if calculated_amount > 0 else float(monthly_fee), 
                    step=100.0
                )

            ref_id = st.text_input("Transaction ID / Reference No. *", placeholder="e.g., UPI/4261908234 or Cheque #109283")

            st.markdown("---")
            st.markdown("#### 📑 Optional Information")
            c3, c4 = st.columns(2)
            with c3:
                payer_name = st.text_input("Payer Name", placeholder="Name on Account/UPI")
            with c4:
                bank_name = st.text_input("Bank / Payment App", placeholder="e.g., Google Pay, HDFC")

            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Advance payment for upcoming months.")

            st.markdown("---")
            allow_duplicate = st.checkbox("⚠️ Force Submission / Allow Duplicate Payment for selected month(s)")

            submit_payment = st.form_submit_button("🚀 Record Payment")

        if submit_payment:
            if not ref_id.strip():
                st.error("❌ Transaction ID / Reference No. is required.")
            elif not selected_months:
                st.error("❌ Please select at least one month.")
            else:
                existing_records = run_query(
                    "SELECT timestamp, months_paid, txn_id FROM payment_history WHERE flat=?", 
                    (selected_flat,)
                )

                duplicate_found = False
                conflicting_months = []

                if not existing_records.empty:
                    for _, row in existing_records.iterrows():
                        past_months = [m.strip() for m in str(row['months_paid']).split(',')]
                        for m in selected_months:
                            if m in past_months:
                                duplicate_found = True
                                conflicting_months.append(f"{m} (Recorded on {row['timestamp']} | Ref: {row['txn_id']})")

                if duplicate_found and not allow_duplicate:
                    st.error(f"🚨 **Duplicate Payment Warning for Flat {selected_flat}!**")
                    st.warning("The selected month(s) are already paid:")
                    for dup in set(conflicting_months):
                        st.write(f"• **{dup}**")
                    st.info("💡 To force duplicate insertion, check **'⚠️ Force Submission / Allow Duplicate Payment'** and click Submit again.")
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

    # -------------------------------------------------------------------------
    # TAB 2: PAYMENT HISTORY LOG
    # -------------------------------------------------------------------------
    with t2:
        st.subheader("📜 Payment History Log")
        
        history_df = run_query("""
            SELECT id, timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks 
            FROM payment_history 
            ORDER BY id DESC
        """)

        if history_df.empty:
            st.info("No payment records found in the database.")
        else:
            c_filter1, c_filter2 = st.columns(2)
            with c_filter1:
                flat_filter = st.selectbox("Filter by Flat", ["All"] + flat_list)
            with c_filter2:
                search_term = st.text_input("Search Reference ID / Remarks", "")

            filtered_df = history_df.copy()
            if flat_filter != "All":
                filtered_df = filtered_df[filtered_df["flat"] == flat_filter]
            if search_term:
                filtered_df = filtered_df[
                    filtered_df["txn_id"].astype(str).str.contains(search_term, case=False) |
                    filtered_df["remarks"].astype(str).str.contains(search_term, case=False)
                ]

            st.dataframe(
                filtered_df,
                column_config={
                    "id": "ID",
                    "timestamp": "Timestamp",
                    "flat": "Flat",
                    "months_paid": "Month(s) Covered",
                    "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
                    "payment_mode": "Method",
                    "txn_id": "Transaction Ref",
                    "remarks": "Remarks"
                },
                hide_index=True,
                use_container_width=True
            )

    # -------------------------------------------------------------------------
    # TAB 3: CONFIG & RATE HISTORY
    # -------------------------------------------------------------------------
    with t3:
        st.subheader("⚙️ Maintenance Rate Configuration")
        
        with st.form("rate_config_form"):
            new_rate = st.number_input("New Monthly Rate (₹)", min_value=100.0, value=float(monthly_fee), step=100.0)
            changed_by = st.text_input("Updated By", value="Admin")
            reason = st.text_area("Reason for Revision", placeholder="e.g., Increased diesel costs for generator.")
            submit_rate = st.form_submit_button("Update Monthly Maintenance Fee")

        if submit_rate:
            if new_rate != monthly_fee:
                execute_db("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', ?)", (str(new_rate),))
                execute_db("""
                    INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monthly_fee, new_rate, changed_by, reason))
                st.success(f"✅ Maintenance fee updated from ₹{monthly_fee} to ₹{new_rate}!")
                st.rerun()

        st.markdown("---")
        st.subheader("📜 Maintenance Fee Change Log")
        rate_log_df = run_query("SELECT * FROM maintenance_config_history ORDER BY id DESC")
        st.dataframe(rate_log_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 3: EXPENSE & CORPUS MANAGEMENT
# -----------------------------------------------------------------------------
elif page == "💸 Expense & Corpus Management":
    st.title("💸 Expense & Corpus Management")
    
    e1, e2 = st.tabs(["🧾 Daily Operating Expenses", "🏦 Corpus Fund Ledger"])

    with e1:
        st.subheader("Log Operating Expense")
        with st.form("expense_form"):
            exp_date = st.date_input("Date", datetime.now().date())
            cat = st.selectbox("Category", ["Electricity Bill", "Water Tanker", "Security Guard Salary", "Cleaning Supplies", "Repairs", "Misc"])
            desc = st.text_input("Description / Paid To")
            amt = st.number_input("Amount (₹)", min_value=1.0, step=50.0)
            sub_exp = st.form_submit_button("Log Expense")

        if sub_exp:
            execute_db("INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
                       (exp_date.strftime("%Y-%m-%d"), cat, desc, amt))
            st.success("Expense logged!")
            st.rerun()

        st.markdown("---")
        exp_df = run_query("SELECT * FROM expenses ORDER BY id DESC")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

    with e2:
        st.subheader("Corpus Fund Transactions")
        corpus_df = run_query("SELECT * FROM corpus ORDER BY id DESC")
        st.dataframe(corpus_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 4: AMC & VENDOR MANAGEMENT
# -----------------------------------------------------------------------------
elif page == "🛠️ AMC & Vendor Management":
    st.title("🛠️ AMC & Equipment Schedules")
    amc_df = run_query("SELECT * FROM amc_schedules ORDER BY next_due ASC")
    st.dataframe(amc_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 5: COMPLAINTS & HELPDESK
# -----------------------------------------------------------------------------
elif page == "🚨 Complaints & Helpdesk":
    st.title("🚨 Complaints & Ticket Helpdesk")
    
    with st.form("issue_form"):
        issue_flat = st.selectbox("Flat", ["101", "102", "201", "202", "301"])
        issue_cat = st.selectbox("Category", ["Plumbing", "Electrical", "Lift", "Security", "Other"])
        issue_desc = st.text_area("Issue Description")
        sub_issue = st.form_submit_button("Raise Ticket")

    if sub_issue:
        execute_db("INSERT INTO issues (date, flat, category, issue, status) VALUES (?, ?, ?, ?, ?)",
                   (datetime.now().strftime("%Y-%m-%d"), issue_flat, issue_cat, issue_desc, "Open"))
        st.success("Ticket submitted!")
        st.rerun()

    st.markdown("---")
    issues_df = run_query("SELECT * FROM issues ORDER BY id DESC")
    st.dataframe(issues_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 6: MEETINGS & MOM LOG
# -----------------------------------------------------------------------------
elif page == "📅 Meetings & MoM Log":
    st.title("📅 General Body Meetings & Minutes")
    meetings_df = run_query("SELECT * FROM meetings ORDER BY id DESC")
    st.dataframe(meetings_df, use_container_width=True, hide_index=True)
