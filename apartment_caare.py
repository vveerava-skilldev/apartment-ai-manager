import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="Apartment AI Manager", layout="wide", page_icon="🏢")

# -----------------------------------------------------------------------------
# INITIALIZE DATABASE (Session State Persistence)
# -----------------------------------------------------------------------------
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "flats_data" not in st.session_state:
    st.session_state.flats_data = pd.DataFrame([
        {"Flat": "101", "Resident": "Sharma", "Monthly_Due": 1000, "Status": "Paid", "Last_Paid": "2026-09-01"},
        {"Flat": "102", "Resident": "Verma", "Monthly_Due": 1000, "Status": "Pending", "Last_Paid": "-"},
        {"Flat": "201", "Resident": "Rao", "Monthly_Due": 1000, "Status": "Paid", "Last_Paid": "2026-09-03"},
        {"Flat": "202", "Resident": "Gupta", "Monthly_Due": 1000, "Status": "Pending", "Last_Paid": "-"},
        {"Flat": "301", "Resident": "Patel", "Monthly_Due": 1000, "Status": "Paid", "Last_Paid": "2026-09-05"},
    ])

if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame([
        {"Date": "2026-09-01", "Category": "Watchman Salary", "Description": "Monthly Watchman Fee", "Amount": 8000},
        {"Date": "2026-09-05", "Category": "Tank Cleaning", "Description": "Overhead Tank Cleansing", "Amount": 2500},
    ])

if "amc_schedule" not in st.session_state:
    st.session_state.amc_schedule = pd.DataFrame([
        {"Equipment": "Water Softener System", "Vendor": "Zero B Care", "Next_Service_Due": "2026-10-15", "Alert_Days": 30},
        {"Equipment": "Lift / Elevator", "Vendor": "Otis India", "Next_Service_Due": "2026-09-25", "Alert_Days": 10},
        {"Equipment": "Water Tank Cleaning", "Vendor": "CleanAqua", "Next_Service_Due": "2026-12-01", "Alert_Days": 15},
    ])

if "issues" not in st.session_state:
    st.session_state.issues = pd.DataFrame([
        {"ID": 1, "Date": "2026-09-10", "Flat": "202", "Category": "Plumbing", "Issue": "Terrace pipe leakage", "Status": "Open"}
    ])

# -----------------------------------------------------------------------------
# SIDEBAR & AUTHENTICATION
# -----------------------------------------------------------------------------
st.sidebar.title("🏢 Navigation")
page = st.sidebar.radio("Go to:", [
    "📊 Public Dashboard", 
    "🤖 AI Voice/Text Command", 
    "📅 AMC & Tank Schedules", 
    "🚨 Report an Issue", 
    "⚙️ Admin Portal"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🔒 Admin Authentication")
if not st.session_state.admin_authenticated:
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if pwd == "admin123":  # Change your passcode here
            st.session_state.admin_authenticated = True
            st.sidebar.success("Logged in as Admin")
            st.rerun()
        else:
            st.sidebar.error("Incorrect Password")
else:
    st.sidebar.write("🟢 Admin Access Active")
    if st.sidebar.button("Logout Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()

# -----------------------------------------------------------------------------
# PAGE 1: PUBLIC DASHBOARD
# -----------------------------------------------------------------------------
if page == "📊 Public Dashboard":
    st.title("🏢 Apartment Maintenance Dashboard")
    
    # Calculate Metrics
    paid_flats = (st.session_state.flats_data["Status"] == "Paid").sum()
    pending_amount = st.session_state.flats_data[st.session_state.flats_data["Status"] == "Pending"]["Monthly_Due"].sum()
    total_expenses = st.session_state.expenses["Amount"].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Flats Paid (This Month)", f"{paid_flats} / 5")
    col2.metric("⚠️ Pending Dues Total", f"₹{pending_amount:,.0f}")
    col3.metric("📉 Total Expenses Logged", f"₹{total_expenses:,.0f}")

    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📋 Maintenance Collection Status")
        st.dataframe(st.session_state.flats_data, use_container_width=True, hide_index=True)
    with col_right:
        st.subheader("🧾 Recent Expenses Log")
        st.dataframe(st.session_state.expenses, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 2: AI VOICE / TEXT AUTOMATION
# -----------------------------------------------------------------------------
elif page == "🤖 AI Voice/Text Command":
    st.title("🤖 Voice & Text Command Automation")
    st.caption("Type or use mobile speech-to-text to issue commands naturally.")
    
    st.info("💡 **Examples:**\n- *Paid 1000 for Flat 102*\n- *Logged expense 8000 for Watchman Salary*\n- *Add issue Flat 101 corridor light not working*")

    user_prompt = st.text_input("🎙️ Voice/Text Input Command:")
    
    if st.button("Process Command") and user_prompt:
        cmd = user_prompt.lower()
        
        # Intent 1: Payment processing
        if "paid" in cmd or "payment" in cmd:
            flat_match = re.search(r'\b(101|102|201|202|301)\b', cmd)
            if flat_match:
                flat_no = flat_match.group(1)
                idx = st.session_state.flats_data[st.session_state.flats_data["Flat"] == flat_no].index[0]
                st.session_state.flats_data.at[idx, "Status"] = "Paid"
                st.session_state.flats_data.at[idx, "Last_Paid"] = str(datetime.now().date())
                st.success(f"🤖 AI Action: Updated Flat {flat_no} maintenance status to PAID.")
            else:
                st.warning("🤖 AI Assistant: Could not identify a valid flat number (101, 102, 201, 202, 301).")
                
        # Intent 2: Expense logging
        elif "expense" in cmd or "logged" in cmd or "spent" in cmd:
            amt_match = re.search(r'\b(\d+)\b', cmd)
            amt = int(amt_match.group(1)) if amt_match else 0
            
            category = "General Expense"
            if "watchman" in cmd: category = "Watchman Salary"
            elif "tank" in cmd: category = "Tank Cleaning"
            elif "electricity" in cmd: category = "Common Electricity"
            
            new_exp = pd.DataFrame([{
                "Date": str(datetime.now().date()),
                "Category": category,
                "Description": user_prompt,
                "Amount": amt
            }])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_exp], ignore_index=True)
            st.success(f"🤖 AI Action: Added expense ₹{amt} under category '{category}'.")
            
        # Intent 3: Issue Reporting
        elif "issue" in cmd or "repair" in cmd or "broken" in cmd:
            flat_match = re.search(r'\b(101|102|201|202|301)\b', cmd)
            flat_no = flat_match.group(1) if flat_match else "General"
            new_issue = pd.DataFrame([{
                "ID": len(st.session_state.issues) + 1,
                "Date": str(datetime.now().date()),
                "Flat": flat_no,
                "Category": "General",
                "Issue": user_prompt,
                "Status": "Open"
            }])
            st.session_state.issues = pd.concat([st.session_state.issues, new_issue], ignore_index=True)
            st.success(f"🤖 AI Action: Logged new issue for Flat {flat_no}.")

# -----------------------------------------------------------------------------
# PAGE 3: AMC & TANK SCHEDULES
# -----------------------------------------------------------------------------
elif page == "📅 AMC & Tank Schedules":
    st.title("📅 AMC & Equipment Maintenance Tracking")
    
    st.subheader("🔔 Upcoming Service & Tank Cleaning Alerts")
    
    for idx, row in st.session_state.amc_schedule.iterrows():
        due_date = datetime.strptime(row["Next_Service_Due"], "%Y-%m-%d").date()
        days_left = (due_date - datetime.now().date()).days
        
        if days_left <= row["Alert_Days"]:
            st.error(f"⚠️ **ALERT:** {row['Equipment']} ({row['Vendor']}) is due in **{days_left} days** (Due: {row['Next_Service_Due']})")
        else:
            st.info(f"✅ **OK:** {row['Equipment']} due in {days_left} days (Due: {row['Next_Service_Due']})")

    st.markdown("---")
    st.subheader("📋 AMC Master Registry")
    st.dataframe(st.session_state.amc_schedule, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 4: REPORT AN ISSUE
# -----------------------------------------------------------------------------
elif page == "🚨 Report an Issue":
    st.title("🚨 Resident Issue Reporting Portal")
    
    with st.form("issue_form"):
        flat = st.selectbox("Select Flat Number", ["101", "102", "201", "202", "301"])
        cat = st.selectbox("Category", ["Plumbing", "Electrical", "Elevator", "Water Softener", "Other"])
        desc = st.text_area("Describe the Issue")
        submitted = st.form_submit_button("Submit Complaint")
        
        if submitted and desc:
            new_iss = pd.DataFrame([{
                "ID": len(st.session_state.issues) + 1,
                "Date": str(datetime.now().date()),
                "Flat": flat,
                "Category": cat,
                "Issue": desc,
                "Status": "Open"
            }])
            st.session_state.issues = pd.concat([st.session_state.issues, new_iss], ignore_index=True)
            st.success("Issue submitted successfully!")

    st.markdown("---")
    st.subheader("📋 Active Building Issues")
    st.dataframe(st.session_state.issues, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PAGE 5: ADMIN PORTAL (Privileged Access)
# -----------------------------------------------------------------------------
elif page == "⚙️ Admin Portal":
    st.title("⚙️ Administrative Control Center")
    
    if not st.session_state.admin_authenticated:
        st.warning("🔒 Access Restricted. Please log in as Admin using the sidebar to modify or delete data.")
    else:
        tab_pay, tab_exp, tab_amc, tab_iss = st.tabs(["Manage Payments", "Manage Expenses", "Manage AMCs", "Manage Issues"])
        
        # Admin - Payments
        with tab_pay:
            st.subheader("Modify Payment Status")
            edited_flats = st.data_editor(st.session_state.flats_data, num_rows="dynamic", key="editor_flats")
            if st.button("Save Payment Changes"):
                st.session_state.flats_data = edited_flats
                st.success("Payment records updated!")

        # Admin - Expenses
        with tab_exp:
            st.subheader("Modify / Delete Expenses")
            edited_exp = st.data_editor(st.session_state.expenses, num_rows="dynamic", key="editor_exp")
            if st.button("Save Expense Changes"):
                st.session_state.expenses = edited_exp
                st.success("Expense records updated!")

        # Admin - AMCs
        with tab_amc:
            st.subheader("Add / Edit AMC Schedules")
            edited_amc = st.data_editor(st.session_state.amc_schedule, num_rows="dynamic", key="editor_amc")
            if st.button("Save AMC Changes"):
                st.session_state.amc_schedule = edited_amc
                st.success("AMC records updated!")

        # Admin - Issues
        with tab_iss:
            st.subheader("Resolve / Delete Reported Issues")
            edited_iss = st.data_editor(st.session_state.issues, num_rows="dynamic", key="editor_iss")
            if st.button("Save Issue Changes"):
                st.session_state.issues = edited_iss
                st.success("Issue records updated!")