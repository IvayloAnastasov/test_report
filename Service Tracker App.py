import streamlit as st
import json
from datetime import datetime, timedelta

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------- CONFIGURATION ----------------------

SPREADSHEET_ID = "1tTjNIHuwQ0PcsfK2Si7IjLP_S0ZeJLmo7C1yMyGqw18"  # 🔧 your sheet ID
WORKSHEET_NAME = "Sheet1"  # 🔧 tab name, change if different

# Scopes needed for gspread / Google Sheets & Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------- GOOGLE SHEETS FUNCTIONS ----------------------

def get_gsheet_client():
    """Authorize and return a gspread client using service account credentials."""
    creds_dict = st.secrets["google_service_account"]  # <-- ensure you have this in secrets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
    client = gspread.authorize(creds)
    return client

def get_worksheet():
    """Return the worksheet object where tasks will be stored."""
    client = get_gsheet_client()
    # Open the Google Sheet by its ID
    sh = client.open_by_key(SPREADSHEET_ID)
    # Select the worksheet/tab
    ws = sh.worksheet(WORKSHEET_NAME)
    return ws

def append_task_to_sheet(task, tech_name):
    """Append a row for a newly added task."""
    ws = get_worksheet()
    row = [
        task["id"],
        tech_name,
        task["description"],
        task["created_at"],
        "Pending",           # status when added
        ""                   # no completed date yet
    ]
    ws.append_row(row, value_input_option='USER_ENTERED')

def update_task_status_in_sheet(task_id, completed_at):
    """
    Find the row with this task_id and update status + completed_at.
    Assumes first row is headers, and columns are:
    ID | Technician | Description | Created At | Status | Completed At
    """
    ws = get_worksheet()
    all_records = ws.get_all_records()  # returns list of dicts mapping headers to values
    # Find which row number, starting from 2 because row 1 is headers
    for idx, rec in enumerate(all_records, start=2):
        # rec["ID"] if your header is "ID", case sensitive
        if str(rec.get("ID")) == str(task_id):
            ws.update_cell(idx, 5, "Done")           # Column E = Status
            ws.update_cell(idx, 6, completed_at)     # Column F = Completed At
            break

# ---------------------- TASK MANAGEMENT ----------------------

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

def add_technician_ui():
    st.subheader("Add Technician")
    name = st.text_input("Name", key="tech_name")
    phone = st.text_input("Phone", key="tech_phone")
    email = st.text_input("Email", key="tech_email")

    if st.button("Add Technician"):
        if not name.strip():
            st.warning("Name is required")
        else:
            techs = st.session_state.tech
            existing_tech = next((t for t in techs if t["name"].lower() == name.strip().lower()), None)
            if existing_tech:
                existing_tech["phone"] = phone.strip()
                existing_tech["email"] = email.strip()
                st.success(f"Updated technician '{name.strip()}'")
            else:
                new_id = 1 + max([t["id"] for t in techs], default=0)
                techs.append({
                    "id": new_id,
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "email": email.strip()
                })
                st.success(f"Added technician '{name.strip()}'")
            st.session_state.tech = techs
            st.session_state["tech_name"] = ""
            st.session_state["tech_phone"] = ""
            st.session_state["tech_email"] = ""

def list_technicians_ui():
    st.subheader("Technicians")
    techs = st.session_state.tech
    if not techs:
        st.write("No technicians yet.")
    else:
        for t in techs:
            st.write(f"ID {t['id']}: {t['name']} | Phone: {t.get('phone','')} | Email: {t.get('email','')}")

def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    if not techs:
        st.warning("Add a technician first.")
        return
    tasks = st.session_state.tasks
    tech_options = {t["name"]: t["id"] for t in techs}
    selected_tech = st.selectbox("Assign to Technician", list(tech_options.keys()), key="task_tech")
    description = st.text_input("Task Description", key="task_desc")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description is required.")
        else:
            new_id = 1 + max([t["id"] for t in tasks], default=0)
            task = {
                "id": new_id,
                "technician_id": tech_options[selected_tech],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            }
            tasks.append(task)
            st.session_state.tasks = tasks
            st.success(f"Task added: {description.strip()}")
            st.session_state["task_desc"] = ""

            # ---- HERE: after you add task, append to Google Sheet ----
            tech_name = get_technician_name(techs, task["technician_id"])
            append_task_to_sheet(task, tech_name)

def list_tasks_ui(show_all=True):
    st.subheader("Tasks")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    if not tasks:
        st.write("No tasks yet.")
        return
    for task in tasks:
        if not show_all and task["done"]:
            continue
        status = "✅ Done" if task["done"] else "❗ Pending"
        tech_name = get_technician_name(techs, task["technician_id"])
        created = datetime.fromisoformat(task["created_at"]).strftime("%Y-%m-%d")
        st.write(f"ID {task['id']}: {task['description']} (Tech: {tech_name}) — Created: {created} — Status: {status}")

def mark_task_done_ui():
    st.subheader("Mark Task as Done")
    tasks = st.session_state.tasks
    pending_tasks = [t for t in tasks if not t["done"]]
    if not pending_tasks:
        st.write("No pending tasks.")
        return
    options = {f"ID {t['id']}: {t['description']}": t["id"] for t in pending_tasks}
    sel = st.selectbox("Select task to mark done", list(options.keys()), key="task_done_sel")
    if st.button("Mark as Done"):
        task_id = options[sel]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                st.session_state.tasks = tasks
                st.success(f"Task ID {task_id} marked done.")
                # ---- HERE: update Google Sheet for status/completed date ----
                update_task_status_in_sheet(task_id, t["completed_at"])
                break

def report_ui():
    st.subheader("Report: Tasks Completed in Last 30 Days")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    cutoff = datetime.now() - timedelta(days=30)
    done_tasks = [t for t in tasks if t["done"] and t.get("completed_at") and datetime.fromisoformat(t["completed_at"]) >= cutoff]
    if not done_tasks:
        st.write("No tasks completed in last 30 days.")
    else:
        for t in done_tasks:
            tech_name = get_technician_name(techs, t["technician_id"])
            comp = datetime.fromisoformat(t["completed_at"]).strftime("%Y-%m-%d")
            st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Completed: {comp}")

def main():
    st.title("Service Tracker with Google Sheets Sync")

    if "tech" not in st.session_state:
        st.session_state.tech = []
    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    menu = [
        "Home",
        "Add Technician",
        "List Technicians",
        "Add Task",
        "List Tasks",
        "Mark Task Done",
        "Report Last 30 Days",
    ]

    st.sidebar.title("Menu")
    selected = st.sidebar.radio("Navigate", menu)
    st.subheader(selected)

    if selected == "Home":
        st.write("Welcome to the Service Tracker App!")
    elif selected == "Add Technician":
        add_technician_ui()
    elif selected == "List Technicians":
        list_technicians_ui()
    elif selected == "Add Task":
        add_task_ui()
    elif selected == "List Tasks":
        show_all = st.checkbox("Show all (including done)", value=True, key="show_all_tasks")
        list_tasks_ui(show_all=show_all)
    elif selected == "Mark Task Done":
        mark_task_done_ui()
    elif selected == "Report Last 30 Days":
        report_ui()
    else:
        st.write("Unknown option.")

if __name__ == "__main__":
    main()
