import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --------------------- CONFIG ---------------------
SHEET_ID = "your_google_sheet_id_here"  # 🔧 Replace with your Google Sheet ID
SHEET_NAME = "Sheet1"                   # 🔧 Sheet/tab name

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

# --------------------- SHEET FUNCTIONS ---------------------

def append_task_to_sheet(task, tech_name):
    service = get_sheets_service()
    values = [[
        task["id"],
        tech_name,
        task["description"],
        task["created_at"],
        "Pending",
        ""
    ]]
    body = {"values": values}
    service.values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def update_task_status_in_sheet(task_id, completed_at):
    service = get_sheets_service()
    result = service.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A2:F"
    ).execute()

    rows = result.get("values", [])
    for i, row in enumerate(rows):
        if str(row[0]) == str(task_id):
            row_number = i + 2
            service.values().update(
                spreadsheetId=SHEET_ID,
                range=f"{SHEET_NAME}!E{row_number}:F{row_number}",
                valueInputOption="USER_ENTERED",
                body={"values": [["Done", completed_at]]}
            ).execute()
            break

# --------------------- UI & LOGIC ---------------------

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
            existing = next((t for t in techs if t["name"].lower() == name.lower()), None)
            if not existing:
                new_id = 1 + max([t["id"] for t in techs], default=0)
                techs.append({"id": new_id, "name": name.strip()})
                st.success(f"Added technician '{name}'")
                st.session_state.tech = techs
            else:
                st.warning("Technician already exists")

def list_technicians_ui():
    st.subheader("Technicians")
    for t in st.session_state.tech:
        st.write(f"{t['id']}: {t['name']}")

def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    if not techs:
        st.warning("Add a technician first.")
        return

    tech_map = {t["name"]: t["id"] for t in techs}
    tech_name = st.selectbox("Assign to", list(tech_map.keys()))
    description = st.text_input("Task Description")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description required.")
        else:
            tasks = st.session_state.tasks
            new_id = 1 + max([t["id"] for t in tasks], default=0)
            task = {
                "id": new_id,
                "technician_id": tech_map[tech_name],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            }
            tasks.append(task)
            st.session_state.tasks = tasks
            st.success("Task added.")

            # 🔄 Sync to Google Sheet
            append_task_to_sheet(task, tech_name)

def list_tasks_ui():
    st.subheader("All Tasks")
    for t in st.session_state.tasks:
        tech = get_technician_name(st.session_state.tech, t["technician_id"])
        status = "✅ Done" if t["done"] else "❗ Pending"
        st.write(f"ID {t['id']}: {t['description']} - {tech} - {status}")

def mark_task_done_ui():
    st.subheader("Mark Task as Done")
    tasks = [t for t in st.session_state.tasks if not t["done"]]
    if not tasks:
        st.info("No pending tasks.")
        return

    task_map = {f"ID {t['id']}: {t['description']}": t["id"] for t in tasks}
    selection = st.selectbox("Select task", list(task_map.keys()))
    if st.button("Mark Done"):
        task_id = task_map[selection]
        for t in st.session_state.tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                update_task_status_in_sheet(task_id, t["completed_at"])
                st.success(f"Marked task {task_id} as done.")
                break

def report_ui():
    st.subheader("Tasks Completed (Last 30 Days)")
    cutoff = datetime.now() - timedelta(days=30)
    for t in st.session_state.tasks:
        if t["done"] and t["completed_at"]:
            done_date = datetime.fromisoformat(t["completed_at"])
            if done_date >= cutoff:
                tech = get_technician_name(st.session_state.tech, t["technician_id"])
                st.write(f"{t['description']} - {tech} ✅ {done_date.strftime('%Y-%m-%d')}")

# --------------------- MAIN ---------------------

def main():
    st.title("Service Tracker App (Google Sheets Sync)")

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
        "Completed Tasks Report"
    ]

    choice = st.sidebar.radio("Menu", menu)
    if choice == "Home":
        st.write("Welcome to the Google Sheets-Connected Task Tracker.")
    elif choice == "Add Technician":
        add_technician_ui()
    elif choice == "List Technicians":
        list_technicians_ui()
    elif choice == "Add Task":
        add_task_ui()
    elif choice == "List Tasks":
        list_tasks_ui()
    elif choice == "Mark Task Done":
        mark_task_done_ui()
    elif choice == "Completed Tasks Report":
        report_ui()

if __name__ == "__main__":
    main()
