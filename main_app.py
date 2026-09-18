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
    
    # Global System Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Rate History Log
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

    # Operational Expenses
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

    # Corpus Fund
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

    # Database Schema Migrations Guard
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

    # Seed Initial Data on First Run
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

    conn.commit()
    conn.close()

# Initialize DB on load
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
# 3. STREAMLIT UI CONFIGURATION & NAVIGATION
# =============================================================================
st.set_page_config(
    page_title="Sri Krishna Mani Apartments Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

monthly_fee = get_monthly_fee()

st.sidebar.title("🏢 Housing Portal")
st.sidebar.caption("Sri Krishna Mani Apartments")

page = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Executive Dashboard",
        "💳 Maintenance & Payments",
        "💸 Expense & Corpus Ledger",
        "🛠️ AMC & Vendor Contracts",
        "🚨 Resident Helpdesk",
        "📅 Meetings & MoM Logs",
        "⚙️ Admin & Flat Settings"
    ]
)

st.sidebar.markdown("---")
current_flat_context = st.sidebar.selectbox("Active Flat Selector", ["All Flats"] + run_query("SELECT flat FROM flats ORDER BY flat")["flat"].tolist())

# =============================================================================
# PAGE 1: EXECUTIVE DASHBOARD
# =============================================================================
if page == "📊 Executive Dashboard":
    st.title("📊 Executive Dashboard")
    st.caption(f"Real-time summary for {datetime.now().strftime('%B %Y')}")

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
    kpi3.metric("Corpus Fund Balance", f"₹{total_corpus:,.2f}")
    kpi4.metric("Open Helpdesk Tickets", f"{pending_tickets} Pending", delta_color="inverse")

    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🏠 Flat Payment Status Matrix")
        st.dataframe(
            flats_df,
            column_config={
                "flat": "Flat No",
                "owner_name": "Owner Name",
                "contact": "Contact",
                "status": "Current Month Status",
                "last_paid": "Last Transaction Date"
            },
            hide_index=True,
            use_container_width=True
        )

    with col_right:
        st.subheader("⚠️ Urgent Action Items")
        
        # Check upcoming AMCs
        amc_alert_df = run_query("SELECT equipment, next_due, vendor FROM amc_schedules ORDER BY next_due ASC LIMIT 3")
        st.markdown("**Upcoming Vendor Renewals:**")
        if not amc_alert_df.empty:
            for _, row in amc_alert_df.iterrows():
                st.warning(f"🔧 **{row['equipment']}** due on `{row['next_due']}` ({row['vendor']})")
        else:
            st.info("No immediate AMC renewals.")

        # Check Unresolved Urgent Helpdesk Issues
        open_issues = run_query("SELECT flat, category, issue FROM issues WHERE status='Open' LIMIT 3")
        st.markdown("**Unresolved Complaints:**")
        if not open_issues.empty:
            for _, row in open_issues.iterrows():
                st.error(f"🚨 **Flat {row['flat']}** ({row['category']}): {row['issue'][:40]}...")
        else:
            st.success("No open complaints!")

# =============================================================================
# PAGE 2: MAINTENANCE & PAYMENTS
# =============================================================================
elif page == "💳 Maintenance & Payments":
    st.title("💳 Maintenance & Payment Portal")
    st.info(f"Configured Standard Maintenance Rate: **₹{monthly_fee:,.2f} / month** per flat.")

    t1, t2 = st.tabs(["💳 Record Payment", "📜 Payment History Log"])

    # -------------------------------------------------------------------------
    # TAB 1: RECORD PAYMENT
    # -------------------------------------------------------------------------
    with t1:
        st.subheader("💳 Record Maintenance Receipt")

        flats_df = run_query("SELECT flat FROM flats ORDER BY flat")
        flat_list = flats_df["flat"].tolist() if not flats_df.empty else ["101", "102", "201", "202", "301"]
        
        # Determine flat context
        selected_flat = st.selectbox(
            "Select Flat Number *", 
            flat_list,
            index=flat_list.index(current_flat_context) if (current_flat_context in flat_list) else 0
        )

        now = datetime.now()
        current_month_str = get_month_str(now)
        next_month_str = get_next_month_str(now)

        # Query Database for Paid Status
        paid_records = run_query("SELECT months_paid FROM payment_history WHERE flat=?", (selected_flat,))
        is_current_month_paid = False
        
        if not paid_records.empty:
            for _, row in paid_records.iterrows():
                paid_months = [m.strip() for m in str(row['months_paid']).split(',')]
                if current_month_str in paid_months:
                    is_current_month_paid = True
                    break

        # Dynamic Notification Banner
        if is_current_month_paid:
            st.success(f"✅ **Flat {selected_flat} HAS PAID for current month ({current_month_str}).** Defaulting to next cycle.")
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
            st.markdown("#### 📌 Mandatory Payment Details")
            
            c1, c2 = st.columns(2)
            with c1:
                pay_mode = st.selectbox("Payment Method *", ["UPI / QR Code", "Net Banking / NEFT", "Cheque", "Cash"])
                payment_date = st.date_input("Date of Payment *", value=now.date())

            with c2:
                selected_months = st.multiselect(
                    "Select Payment Month(s) / Advance *", 
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

            ref_id = st.text_input("Transaction ID / Cheque / Ref No. *", placeholder="e.g., UPI/4261908234 or Cheque #109283")

            st.markdown("---")
            st.markdown("#### 📑 Payer & Bank Metadata")
            c3, c4 = st.columns(2)
            with c3:
                payer_name = st.text_input("Payer Account Name", placeholder="Name as seen on Bank/UPI Account")
            with c4:
                bank_name = st.text_input("Bank / App", placeholder="e.g., Google Pay, HDFC Bank, PhonePe")

            remarks = st.text_area("Remarks / Notes", placeholder="e.g., Advance payment for upcoming festival months.")

            st.markdown("---")
            allow_duplicate = st.checkbox("⚠️ Allow Duplicate Entry / Force Override for selected month(s)")

            submit_payment = st.form_submit_button("🚀 Submit Payment")

        # Submission & Duplicate Check Logic
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
                    st.error(f"🚨 **Duplicate Payment Detected for Flat {selected_flat}!**")
                    st.warning("The database shows payments already exist for the selected month(s):")
                    for dup in set(conflicting_months):
                        st.write(f"• **{dup}**")
                    st.info("💡 **Action Needed:** To intentionally add a second entry for these month(s), check the **'⚠️ Allow Duplicate Entry'** box and click Submit again.")
                else:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    p_date_str = payment_date.strftime("%Y-%m-%d")
                    months_str = ", ".join(selected_months)

                    # Update Flat Status
                    execute_db("UPDATE flats SET status='Paid', last_paid=? WHERE flat=?", (p_date_str, selected_flat))
                    
                    # Insert Record
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

                    st.success(f"✅ Payment of ₹{paid_amount:,.2f} logged for **Flat {selected_flat}** ({months_str})!")
                    st.balloons()
                    st.rerun()

    # -------------------------------------------------------------------------
    # TAB 2: PAYMENT HISTORY LOG
    # -------------------------------------------------------------------------
    with t2:
        st.subheader("📜 Payment Audit Trail")
        
        history_df = run_query("""
            SELECT id, timestamp, flat, months_paid, amount, payment_mode, txn_id, remarks 
            FROM payment_history 
            ORDER BY id DESC
        """)

        if history_df.empty:
            st.info("No payment records recorded yet.")
        else:
            c_filter1, c_filter2 = st.columns(2)
            with c_filter1:
                flat_filter = st.selectbox("Filter Flat", ["All"] + flat_list)
            with c_filter2:
                search_term = st.text_input("Search Transaction ID / Remarks", "")

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
                    "amount": st.column_config.NumberColumn("Amount Paid", format="₹%.2f"),
                    "payment_mode": "Method",
                    "txn_id": "Reference ID",
                    "remarks": "Notes"
                },
                hide_index=True,
                use_container_width=True
            )

# =============================================================================
# PAGE 3: EXPENSE & CORPUS LEDGER
# =============================================================================
elif page == "💸 Expense & Corpus Ledger":
    st.title("💸 Financial Operations & Ledger")

    e1, e2 = st.tabs(["🧾 Daily Operating Expenses", "🏦 Corpus Fund Ledger"])

    with e1:
        st.subheader("Log Maintenance Expense")
        with st.form("expense_logging_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                exp_date = st.date_input("Expense Date", datetime.now().date())
                cat = st.selectbox("Category", ["Electricity Bill", "Water Tankers", "Security Salary", "Cleaning Supplies", "Lift Servicing", "Plumbing/Electrical", "Misc"])
            with c2:
                amt = st.number_input("Amount (₹) *", min_value=1.0, step=100.0)
                approved_by = st.text_input("Approved By", value="President/Treasurer")
            with c3:
                desc = st.text_area("Vendor / Invoice Description *", placeholder="e.g., Paid CleanAqua for 2 water tankers")
            
            sub_exp = st.form_submit_button("Log Operating Expense")

        if sub_exp:
            if not desc.strip():
                st.error("Please add a description.")
            else:
                execute_db("INSERT INTO expenses (date, category, description, amount, approved_by) VALUES (?, ?, ?, ?, ?)",
                           (exp_date.strftime("%Y-%m-%d"), cat, desc, amt, approved_by))
                st.success("Expense logged successfully!")
                st.rerun()

        st.markdown("---")
        st.subheader("Logged Operating Expenses")
        exp_df = run_query("SELECT id, date, category, description, amount, approved_by FROM expenses ORDER BY id DESC")
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

    with e2:
        st.subheader("Corpus Fund Ledger (Sinking Fund)")
        
        with st.form("corpus_form"):
            c1, c2 = st.columns(2)
            with c1:
                c_date = st.date_input("Transaction Date", datetime.now().date())
                c_type = st.selectbox("Type", ["Contribution", "Major Repair Expense"])
                c_source = st.text_input("Source / Flat / Vendor", value="All Flat Owners")
            with c2:
                c_amt = st.number_input("Amount (₹)", min_value=1.0, step=1000.0)
                c_desc = st.text_area("Purpose / Details", placeholder="e.g., Annual Sinking Fund Deposit")
            
            sub_corpus = st.form_submit_button("Record Corpus Entry")

        if sub_corpus:
            actual_amt = c_amt if c_type == "Contribution" else -c_amt
            execute_db("INSERT INTO corpus (date, type, flat_or_vendor, description, amount) VALUES (?, ?, ?, ?, ?)",
                       (c_date.strftime("%Y-%m-%d"), c_type, c_source, c_desc, actual_amt))
            st.success("Corpus entry recorded!")
            st.rerun()

        st.markdown("---")
        corpus_df = run_query("SELECT * FROM corpus ORDER BY id DESC")
        st.dataframe(corpus_df, use_container_width=True, hide_index=True)

# =============================================================================
# PAGE 4: AMC & VENDOR CONTRACTS
# =============================================================================
elif page == "🛠️ AMC & Vendor Contracts":
    st.title("🛠️ Vendor Contracts & AMC Tracker")

    with st.expander("➕ Register New Equipment AMC / Service Contract"):
        with st.form("amc_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                eq = st.text_input("Equipment / Facility Name *", placeholder="e.g., CCTV Cameras")
                v_name = st.text_input("Vendor Agency *", placeholder="e.g., SecureEye Systems")
            with c2:
                v_contact = st.text_input("Contact Person & Phone", placeholder="e.g., Rajesh (9900112233)")
                next_date = st.date_input("Next Renewal / Due Date")
            with c3:
                cost = st.number_input("Contract Cost (₹)", min_value=0.0, step=500.0)
                alert_days = st.number_input("Alert Lead Time (Days)", min_value=1, value=30)
            
            sub_amc = st.form_submit_button("Save AMC Contract")

        if sub_amc:
            if not eq or not v_name:
                st.error("Equipment and Vendor Name are required.")
            else:
                execute_db("""
                    INSERT INTO amc_schedules (equipment, vendor, contact_person, next_due, cost, alert_days)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (eq, v_name, v_contact, next_date.strftime("%Y-%m-%d"), cost, alert_days))
                st.success("AMC Schedule Saved!")
                st.rerun()

    st.markdown("---")
    st.subheader("Active Annual Maintenance Contracts (AMCs)")
    amc_df = run_query("SELECT * FROM amc_schedules ORDER BY next_due ASC")

    if not amc_df.empty:
        today = datetime.now().date()
        
        # Calculate status tags
        status_list = []
        for _, row in amc_df.iterrows():
            due_dt = datetime.strptime(row['next_due'], "%Y-%m-%d").date()
            days_left = (due_dt - today).days
            if days_left < 0:
                status_list.append("🔴 EXPIRED")
            elif days_left <= row['alert_days']:
                status_list.append(f"⚠️ DUE SOON ({days_left} Days Left)")
            else:
                status_list.append(f"🟢 Active ({days_left} Days Left)")

        amc_df["Status Tag"] = status_list

        st.dataframe(
            amc_df,
            column_config={
                "id": "ID",
                "equipment": "Equipment/Service",
                "vendor": "Vendor Name",
                "contact_person": "Contact Details",
                "next_due": "Renewal Due Date",
                "cost": st.column_config.NumberColumn("Cost (₹)", format="₹%.2f"),
                "alert_days": "Lead Days",
                "Status Tag": "Current Status"
            },
            hide_index=True,
            use_container_width=True
        )

# =============================================================================
# PAGE 5: RESIDENT HELPDESK
# =============================================================================
elif page == "🚨 Resident Helpdesk":
    st.title("🚨 Resident Complaints & Service Tickets")

    t1, t2 = st.tabs(["➕ Raise Ticket", "🛠️ Manage & Resolve Tickets"])

    with t1:
        st.subheader("Submit Maintenance Request")
        with st.form("new_ticket_form"):
            c1, c2 = st.columns(2)
            with c1:
                flat_no = st.selectbox("Flat Number", run_query("SELECT flat FROM flats")["flat"].tolist())
                cat = st.selectbox("Category", ["Plumbing", "Electrical", "Lift/Elevator", "Security", "Cleanliness", "Noise/Disturbance", "Other"])
            with c2:
                issue_text = st.text_area("Issue Description *", placeholder="e.g., Water leakage from 3rd-floor corridor pipe.")
            
            sub_ticket = st.form_submit_button("Submit Helpdesk Ticket")

        if sub_ticket:
            if not issue_text.strip():
                st.error("Please provide details of the issue.")
            else:
                execute_db("INSERT INTO issues (date, flat, category, issue, status) VALUES (?, ?, ?, ?, 'Open')",
                           (datetime.now().strftime("%Y-%m-%d"), flat_no, cat, issue_text))
                st.success("Ticket submitted successfully!")
                st.rerun()

    with t2:
        st.subheader("Manage Active Helpdesk Tickets")
        issues_df = run_query("SELECT * FROM issues ORDER BY id DESC")

        if issues_df.empty:
            st.info("No helpdesk tickets recorded.")
        else:
            for _, row in issues_df.iterrows():
                with st.expander(f"Ticket #{row['id']} - Flat {row['flat']} ({row['category']}) | Status: {row['status']}"):
                    st.write(f"**Date Reported:** {row['date']}")
                    st.write(f"**Issue Description:** {row['issue']}")
                    st.write(f"**Resolution Notes:** {row['resolution_notes'] if row['resolution_notes'] else 'None'}")
                    
                    st.markdown("---")
                    st.markdown("**Update Status:**")
                    with st.form(f"update_ticket_{row['id']}"):
                        new_status = st.selectbox("Status", ["Open", "In Progress", "Resolved"], index=["Open", "In Progress", "Resolved"].index(row['status']))
                        res_notes = st.text_area("Resolution Remarks", value=row['resolution_notes'])
                        update_sub = st.form_submit_button("Update Ticket")

                    if update_sub:
                        execute_db("UPDATE issues SET status=?, resolution_notes=? WHERE id=?", (new_status, res_notes, row['id']))
                        st.success(f"Ticket #{row['id']} updated!")
                        st.rerun()

# =============================================================================
# PAGE 6: MEETINGS & MOM LOGS
# =============================================================================
elif page == "📅 Meetings & MoM Logs":
    st.title("📅 Society Meetings & Minutes of Meeting (MoM)")

    with st.expander("📅 Schedule Meeting / Record MoM"):
        with st.form("meeting_form"):
            c1, c2 = st.columns(2)
            with c1:
                m_title = st.text_input("Meeting Title *", placeholder="e.g., Emergency Water Supply Meeting")
                m_date = st.date_input("Date", datetime.now().date())
                m_time = st.text_input("Time", value="10:00 AM")
            with c2:
                m_attendees = st.text_input("Attendees", value="All Resident Owners")
                m_status = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])
            
            m_summary = st.text_area("Summary / MoM Notes", placeholder="Record decisions taken during the meeting...")
            sub_m = st.form_submit_button("Save Meeting Entry")

        if sub_m:
            if not m_title:
                st.error("Title is required.")
            else:
                execute_db("""
                    INSERT INTO meetings (date, time, title, attendees, summary_mom, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (m_date.strftime("%Y-%m-%d"), m_time, m_title, m_attendees, m_summary, m_status))
                st.success("Meeting record saved!")
                st.rerun()

    st.markdown("---")
    meetings_df = run_query("SELECT * FROM meetings ORDER BY id DESC")
    st.dataframe(
        meetings_df,
        column_config={
            "id": "ID",
            "date": "Date",
            "time": "Time",
            "title": "Title",
            "attendees": "Attendees",
            "summary_mom": "Minutes of Meeting (MoM)",
            "status": "Status"
        },
        hide_index=True,
        use_container_width=True
    )

# =============================================================================
# PAGE 7: ADMIN & FLAT SETTINGS
# =============================================================================
elif page == "⚙️ Admin & Flat Settings":
    st.title("⚙️ System Administration & Master Data")

    t1, t2 = st.tabs(["⚙️ Configure Maintenance Fee", "🏠 Manage Flats Master"])

    with t1:
        st.subheader("Configure Default Maintenance Fee")
        st.info(f"Current System Rate: **₹{monthly_fee:,.2f} / month**")

        with st.form("rate_config_form"):
            new_rate = st.number_input("New Default Rate (₹)", min_value=100.0, value=float(monthly_fee), step=100.0)
            changed_by = st.text_input("Authorizing Person", value="Admin")
            reason = st.text_area("Reason for Tariff Revision", placeholder="e.g., Tariff adjustment due to increased security & diesel charges.")
            submit_rate = st.form_submit_button("Update Standard Rate")

        if submit_rate:
            if new_rate != monthly_fee:
                execute_db("INSERT OR REPLACE INTO settings VALUES ('monthly_maintenance', ?)", (str(new_rate),))
                execute_db("""
                    INSERT INTO maintenance_config_history (timestamp, old_amount, new_amount, changed_by, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), monthly_fee, new_rate, changed_by, reason))
                st.success(f"Standard fee updated to ₹{new_rate}!")
                st.rerun()

        st.markdown("---")
        st.subheader("Rate Revision History")
        rate_log_df = run_query("SELECT * FROM maintenance_config_history ORDER BY id DESC")
        st.dataframe(rate_log_df, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Add / Update Flat Information")
        with st.form("add_flat_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                f_no = st.text_input("Flat Number *", placeholder="e.g., 401")
            with c2:
                f_owner = st.text_input("Owner Name *", placeholder="e.g., J. Patel")
            with c3:
                f_contact = st.text_input("Contact Number", placeholder="+91 9900000000")
            
            sub_flat = st.form_submit_button("Save Flat Record")

        if sub_flat:
            if not f_no or not f_owner:
                st.error("Flat Number and Owner Name are required.")
            else:
                execute_db("INSERT OR REPLACE INTO flats (flat, owner_name, contact) VALUES (?, ?, ?)", (f_no, f_owner, f_contact))
                st.success(f"Flat {f_no} saved successfully!")
                st.rerun()

        st.markdown("---")
        st.dataframe(run_query("SELECT * FROM flats ORDER BY flat"), use_container_width=True, hide_index=True)
