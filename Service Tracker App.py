import streamlit as st
import json
from datetime import datetime, timedelta
import os

# Import gspread and auth
import gspread
from google.oauth2.service_account import Credentials

# ------------------ CONFIG ------------------

SPREADSHEET_ID = "1tTjNIHuwQ0PcsfK2Si7IjLP_S0ZeJLmo7C1yMyGqw18"  # 🔧 your sheet ID
SHEET_NAME = "Sheet1"  # 🔧 tab name, change if different

# Scopes needed for gspread / Google Sheets & Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ------------------ Google Sheet / gspread setup ------------------

def get_worksheet():
    """Returns the worksheet object for editing."""
    # If using secrets, load from st.secrets
    creds_info = st.secrets["google_service_account"]  # put the JSON dict in secrets
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    # Open by key (spreadsheet id)
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME)
    return ws

# ------------------ Task / Technician logic ------------------

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

def add_technician_ui():
    st.subheader("Add Technician")
    name = st.text_input("Name", key="tech_name")
    if st.button("Add Technician"):
        if not name.strip():
            st.warning("Name is required")
        else:
            techs = st.session_state.tech
            existing = next((t for t in techs if t["name"].lower() == name.strip().lower()), None)
            if not existing:
                new_id = 1 + max([t["id"] for t in techs], default=0)
                techs.append({"id": new_id, "name": name.strip()})
                st.session_state.tech = techs
                st.success(f"Added technician '{name.strip()}'")
            else:
                st.warning("Technician already exists")

def list_technicians_ui():
    st.subheader("Technicians")
    techs = st.session_state.tech
    if not techs:
        st.write("No technicians yet.")
    else:
        for t in techs:
            st.write(f"ID {t['id']}: {t['name']}")

def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    if not techs:
        st.warning("Add a technician first.")
        return

    tech_map = {t["name"]: t["id"] for t in techs}
    selected_tech = st.selectbox("Assign to", list(tech_map.keys()), key="task_tech")
    description = st.text_input("Task Description", key="task_desc")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description is required.")
        else:
            tasks = st.session_state.tasks
            new_id = 1 + max([t["id"] for t in tasks], default=0)
            task = {
                "id": new_id,
                "technician_id": tech_map[selected_tech],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            }
            tasks.append(task)
            st.session_state.tasks = tasks
            st.success(f"Task added: {description.strip()}")

            # ---- HERE: sync row to Google Sheet ----
            ws = get_worksheet()
            tech_name = get_technician_name(techs, task["technician_id"])
            # append row: ID | Technician | Description | Created At | Status | Completed At
            ws.append_row([
                task["id"],
                tech_name,
                task["description"],
                task["created_at"],
                "Pending",
                ""
            ])

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
        st.write(f"ID {t['id']}: {t['description']} (Tech: {tech_name}) — Created: {created} — Status: {status}")

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
                st.session_state.tasks = tasks
                st.success(f"Task ID {task_id} marked done.")

                # ---- HERE: update the row in Google Sheet ----
                ws = get_worksheet()
                # find which row has this task_id
                records = ws.get_all_records()
                # records is list of dicts, mapping headers to values
                # find matching record
                for idx, rec in enumerate(records, start=2):  # row 1 is headers
                    if str(rec.get("ID")) == str(task_id):
                        # update status and completed_at
                        ws.update_cell(idx, 5, "Done")
                        ws.update_cell(idx, 6, t["completed_at"])
                        break
                break

def report_ui():
    st.subheader("Report: Tasks Completed in Last 30 Days")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    cutoff = datetime.now() - timedelta(days=30)
    found = False
    for t in tasks:
        if t["done"] and t.get("completed_at"):
            dt = datetime.fromisoformat(t["completed_at"])
            if dt >= cutoff:
                found = True
                tech_name = get_technician_name(techs, t["technician_id"])
                st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Completed: {dt.strftime('%Y-%m-%d')}")
    if not found:
        st.write("No tasks completed in last 30 days.")

def main():
    st.title("Service Tracker (gspread / Google Sheet)")

    # Initialize session state
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
        "Report Last 30 Days"
    ]

    choice = st.sidebar.radio("Navigate", menu)
    st.subheader(choice)

    if choice == "Home":
        st.write("Welcome to Service Tracker")
    elif choice == "Add Technician":
        add_technician_ui()
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
