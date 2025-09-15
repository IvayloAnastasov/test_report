import streamlit as st
import json
from datetime import datetime, timedelta
import requests

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------- CONFIGURATION ----------------------

SPREADSHEET_ID = "1tTjNIHuwQ0PcsfK2Si7IjLP_S0ZeJLmo7C1yMyGqw18"  # your Google Sheet ID
WORKSHEET_NAME = "Sheet1"  # tab name

TECH_GITHUB_URL = "https://raw.githubusercontent.com/IvayloAnastasov/test_report/refs/heads/main/tech_update.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------- GOOGLE SHEETS FUNCTIONS ----------------------

def get_gsheet_client():
    creds_dict = st.secrets["google_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
    client = gspread.authorize(creds)
    return client

def get_worksheet():
    client = get_gsheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)
    return ws

def append_task_to_sheet(task, tech_name):
    ws = get_worksheet()
    row = [
        task["id"],
        tech_name,
        task["description"],
        task["created_at"],
        "Pending",
        ""
    ]
    try:
        ws.append_row(row, value_input_option='USER_ENTERED')
    except Exception as e:
        st.error(f"Failed to append to Google Sheet: {e}")

def update_task_status_in_sheet(task_id, completed_at):
    ws = get_worksheet()
    all_records = ws.get_all_records()
    for idx, rec in enumerate(all_records, start=2):
        if str(rec.get("ID")) == str(task_id):
            ws.update_cell(idx, 5, "Done")           # column E
            ws.update_cell(idx, 6, completed_at)     # column F
            break

def load_tasks_from_sheet():
    ws = get_worksheet()
    records = ws.get_all_records()
    tasks = []
    techs = st.session_state.get("tech", [])

    for rec in records:
        try:
            tech_name = rec.get("Technician")
            tech_id = next((t["id"] for t in techs if t["name"] == tech_name), None)

            task = {
                "id": int(rec.get("ID")),
                "technician_id": tech_id,
                "description": rec.get("Description"),
                "created_at": rec.get("Created At"),
                "done": rec.get("Status") == "Done",
                "completed_at": rec.get("Completed At") if rec.get("Completed At") else None
            }
            tasks.append(task)
        except Exception as e:
            st.warning(f"Skipping row due to error: {e}")
    return tasks

# ---------------------- GITHUB TECHNICIANS LOAD ----------------------

def load_technicians_from_github():
    try:
        resp = requests.get(TECH_GITHUB_URL)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        else:
            st.error("Technicians JSON from GitHub is not a list.")
            return []
    except Exception as e:
        st.error(f"Error loading technicians from GitHub: {e}")
        return []

# ---------------------- TASK MANAGEMENT + UI ----------------------

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

def list_technicians_ui():
    st.subheader("Technicians (from GitHub)")
    techs = st.session_state.tech
    if not techs:
        st.write("No technicians found.")
    else:
        for t in techs:
            phone = t.get("phone", "")
            email = t.get("email", "")
            st.write(f"ID {t['id']}: {t['name']} | Phone: {phone} | Email: {email}")

def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    if not techs:
        st.warning("No technicians available.")
        return

    tech_options = {t["name"]: t["id"] for t in techs}
    selected_tech_name = st.selectbox("Assign to Technician", list(tech_options.keys()), key="task_tech")
    description = st.text_input("Task Description", key="task_desc")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description is required.")
        else:
            ws = get_worksheet()
            existing_tasks = ws.get_all_records()
            existing_ids = [int(t.get("ID", 0)) for t in existing_tasks]
            new_id = max(existing_ids or [0]) + 1

            task = {
                "id": new_id,
                "technician_id": tech_options[selected_tech_name],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            }

            # Save to Google Sheet
            append_task_to_sheet(task, selected_tech_name)

            # Reload tasks from sheet
            st.session_state.tasks = load_tasks_from_sheet()

            st.success(f"Task added: {description.strip()}")
            st.session_state["task_desc"] = ""

def list_tasks_ui(show_all=True):
    st.subheader("Tasks")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    if not tasks:
        st.write("No tasks yet.")
        return
    for t in tasks:
        if not show_all and t["done"]:
            continue
        status = "✅ Done" if t["done"] else "❗ Pending"
        tech_name = get_technician_name(techs, t["technician_id"])
        created = datetime.fromisoformat(t["created_at"]).strftime("%Y-%m-%d")
        st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Created: {created} — Status: {status}")

def mark_task_done_ui():
    st.subheader("Mark Task as Done")
    tasks = st.session_state.tasks
    pending = [t for t in tasks if not t["done"]]
    if not pending:
        st.write("No pending tasks.")
        return
    options = {f"ID {t['id']}: {t['description']}": t["id"] for t in pending}
    sel = st.selectbox("Select task to mark done", list(options.keys()), key="task_done_sel")
    if st.button("Mark as Done"):
        task_id = options[sel]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                update_task_status_in_sheet(task_id, t["completed_at"])
                st.session_state.tasks = load_tasks_from_sheet()
                st.success(f"Task ID {task_id} marked done.")
                break

def report_ui():
    st.subheader("Report: Tasks Completed in Last 30 Days")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    cutoff = datetime.now() - timedelta(days=30)
    done_tasks = [t for t in tasks if t["done"] and t.get("completed_at") and datetime.fromisoformat(t["completed_at"]) >= cutoff]
    if not done_tasks:
        st.write("No tasks completed in the last 30 days.")
    else:
        for t in done_tasks:
            tech_name = get_technician_name(techs, t["technician_id"])
            comp = datetime.fromisoformat(t["completed_at"]).strftime("%Y-%m-%d")
            st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Completed: {comp}")

# ---------------------- MAIN ----------------------

def main():
    st.title("Service Tracker with Techs from GitHub")

    # Load techs from GitHub once
    if "tech" not in st.session_state:
        st.session_state.tech = load_technicians_from_github()

    # Always load tasks from Google Sheets on each app load
    st.session_state.tasks = load_tasks_from_sheet()

    menu = [
        "Home",
        "List Technicians",
        "Add Task",
        "List Tasks",
        "Mark Task Done",
        "Report Last 30 Days"
    ]

    choice = st.sidebar.radio("Navigate", menu)
    st.subheader(choice)

    if choice == "Home":
        st.write("Welcome to Service Tracker App")
    elif choice == "List Technicians":
        list_technicians_ui()
    elif choice == "Add Task":
        add_task_ui()
    elif choice == "List Tasks":
        show_all = st.checkbox("Show all (including done)", value=True, key="show_all_tasks")
        list_tasks_ui(show_all)
    elif choice == "Mark Task Done":
        mark_task_done_ui()
    elif choice == "Report Last 30 Days":
        report_ui()

if __name__ == "__main__":
    main()
