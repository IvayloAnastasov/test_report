import streamlit as st
import json
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------- CONFIGURATION ----------------------

SPREADSHEET_ID = "1tTjNIHuwQ0PcsfK2Si7IjLP_S0ZeJLmo7C1yMyGqw18"
WORKSHEET_NAME = "Sheet1"
TECHNICIANS_SHEET = "Technicians"

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

def get_worksheet(name):
    client = get_gsheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(name)

def ensure_headers_exist():
    ws = get_worksheet(WORKSHEET_NAME)
    headers = ws.row_values(1)
    expected = ["ID", "Technician", "Description", "Created At", "Status", "Completed At"]
    if headers != expected:
        ws.insert_row(expected, index=1)

# ---------------------- TECHNICIANS ----------------------

def load_technicians_from_sheet():
    try:
        ws = get_worksheet(TECHNICIANS_SHEET)
        records = ws.get_all_records()
        technicians = []
        for r in records:
            technicians.append({
                "id": int(r.get("ID")),
                "name": r.get("Name"),
                "email": r.get("Email", ""),
                "phone": r.get("Phone", "")
            })
        return technicians
    except Exception as e:
        st.error(f"Error loading technicians from Google Sheet: {e}")
        return []

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

# ---------------------- TASKS ----------------------

def append_task_to_sheet(task, tech_name):
    ws = get_worksheet(WORKSHEET_NAME)
    row = [
        task["id"],
        tech_name,
        task["description"],
        task["created_at"],
        "Done" if task["done"] else "Pending",
        task["completed_at"] or ""
    ]
    try:
        ws.append_row(row, value_input_option='USER_ENTERED')
    except Exception as e:
        st.error(f"Failed to append to Google Sheet: {e}")

def update_task_status_in_sheet(task_id, completed_at):
    ws = get_worksheet(WORKSHEET_NAME)
    all_records = ws.get_all_records()
    for idx, rec in enumerate(all_records, start=2):
        if str(rec.get("ID")) == str(task_id):
            ws.update_cell(idx, 5, "Done")           # Status column
            ws.update_cell(idx, 6, completed_at)     # Completed At column
            break

def load_tasks_from_sheet():
    ws = get_worksheet(WORKSHEET_NAME)
    records = ws.get_all_records()

    if "tech" not in st.session_state:
        st.session_state.tech = load_technicians_from_sheet()
    techs = st.session_state.tech

    tasks = []
    for rec in records:
        try:
            tech_name = rec.get("Technician")
            tech_id = next((t["id"] for t in techs if t["name"] == tech_name), None)

            task = {
                "id": int(rec.get("ID")),
                "technician_id": tech_id,
                "description": rec.get("Description", ""),
                "created_at": rec.get("Created At", ""),
                "done": rec.get("Status", "").strip().lower() == "done",
                "completed_at": rec.get("Completed At") or None
            }
            tasks.append(task)
        except Exception as e:
            st.warning(f"Skipping row due to error: {e}")
    return tasks

# ---------------------- UI FUNCTIONS ----------------------

def list_technicians_ui():
    st.subheader("Technicians")
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
            ws = get_worksheet(WORKSHEET_NAME)
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

            append_task_to_sheet(task, selected_tech_name)
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
    
    if not show_all:
        tasks = [t for t in tasks if not t["done"]]

    tasks_data = []
    for t in tasks:
        tech_name = get_technician_name(techs, t["technician_id"])
        created = datetime.fromisoformat(t["created_at"]).strftime("%Y-%m-%d")
        status = "✅ Done" if t["done"] else "❗ Pending"

        tasks_data.append({
            "ID": t["id"],
            "Description": t["description"],
            "Technician": tech_name,
            "Created": created,
            "Status": status
        })

    st.dataframe(tasks_data)

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
        report_data = []
        for t in done_tasks:
            tech_name = get_technician_name(techs, t["technician_id"])
            comp_date = datetime.fromisoformat(t["completed_at"]).strftime("%Y-%m-%d")
            
            report_data.append({
                "ID": t["id"],
                "Description": t["description"],
                "Technician": tech_name,
                "Date Completed": comp_date
            })
        
        st.dataframe(report_data)

# ---------------------- MAIN ----------------------

def main():
    st.set_page_config(layout="wide")
    st.title("🛠️ Service Tracker")

    ensure_headers_exist()

    if "tech" not in st.session_state:
        st.session_state.tech = load_technicians_from_sheet()
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks_from_sheet()
    if "page" not in st.session_state:
        st.session_state.page = "Home"

    # Define navigation icons and labels
    nav_labels = {
        "Home": "🏠",
        "List Technicians": "👨‍🔧",
        "Add Task": "➕",
        "List Tasks": "📋",
        "Mark Task Done": "✅",
        "Report Last 30 Days": "📊"
    }

    # Inject CSS for gray background
    st.markdown("""
        <style>
            .gray-box {
                background-color: #C0C0C0;
                padding: 20px;
                border-radius: 10px;
                height: 100%;
            }
            .gray-box button {
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # Layout: 1 column for nav (left), 1 for content (right)
    nav_col, content_col = st.columns([1, 5])

    # Left vertical nav menu with gray background
    with nav_col:
        with st.container():
            st.markdown('<div class="gray-box">', unsafe_allow_html=True)
            st.markdown("### Menu")
            for label, icon in nav_labels.items():
                if st.button(f"{icon} {label}", key=label):
                    st.session_state.page = label
            st.markdown('</div>', unsafe_allow_html=True)

    # Page content
    with content_col:
        st.subheader(st.session_state.page)

        if st.session_state.page == "Home":
            st.write("Welcome to the Service Tracker App")
        elif st.session_state.page == "List Technicians":
            list_technicians_ui()
        elif st.session_state.page == "Add Task":
            add_task_ui()
        elif st.session_state.page == "List Tasks":
            show_all = st.checkbox("Show all (including done)", value=True, key="show_all_tasks")
            list_tasks_ui(show_all)
        elif st.session_state.page == "Mark Task Done":
            mark_task_done_ui()
        elif st.session_state.page == "Report Last 30 Days":
            report_ui()


if __name__ == "__main__":
    main()
