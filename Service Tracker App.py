import streamlit as st
import json
import os
from datetime import datetime, timedelta

# ----------------------------
# Constants
# ----------------------------
DATA_DIR = "data"
TECH_FILE = os.path.join(DATA_DIR, "tech.json")

# ----------------------------
# Utility Functions for File I/O
# ----------------------------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def save_tech_to_disk():
    ensure_data_dir()
    with open(TECH_FILE, "w") as f:
        json.dump(st.session_state.tech, f, indent=4)

def load_tech_from_disk():
    if os.path.exists(TECH_FILE):
        with open(TECH_FILE, "r") as f:
            st.session_state.tech = json.load(f)
    else:
        st.session_state.tech = []

def export_tech_file():
    tech_data = json.dumps(st.session_state.tech, indent=4)
    st.download_button(
        label="📤 Export Technicians as JSON",
        data=tech_data,
        file_name="tech_export.json",
        mime="application/json"
    )

def import_tech_file():
    uploaded = st.file_uploader("📥 Import Technicians JSON File", type="json")
    if uploaded:
        try:
            tech_data = json.load(uploaded)
            if isinstance(tech_data, list):
                st.session_state.tech = tech_data
                save_tech_to_disk()
                st.success("Technicians imported successfully.")
            else:
                st.error("Invalid file format. Expected a list.")
        except Exception as e:
            st.error(f"Failed to import: {e}")

# ----------------------------
# Initialize session state
# ----------------------------

if "tech" not in st.session_state:
    load_tech_from_disk()

if "tasks" not in st.session_state:
    st.session_state.tasks = []

# ----------------------------
# Helper Functions
# ----------------------------

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

# ----------------------------
# UI Components
# ----------------------------

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
            new_id = 1 + max([t["id"] for t in techs], default=0)
            techs.append({
                "id": new_id,
                "name": name.strip(),
                "phone": phone.strip(),
                "email": email.strip()
            })
            save_tech_to_disk()
            st.success(f"Added technician {name}")
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
            st.write(f"ID {t['id']}: {t['name']} | Phone: {t['phone']} | Email: {t['email']}")

def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    tasks = st.session_state.tasks

    if not techs:
        st.warning("Add a technician first.")
        return

    tech_options = {t["name"]: t["id"] for t in techs}
    selected_tech = st.selectbox("Assign to Technician", options=list(tech_options.keys()), key="task_tech")
    description = st.text_input("Task Description", key="task_desc")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description is required.")
        else:
            new_id = 1 + max([t["id"] for t in tasks], default=0)
            tasks.append({
                "id": new_id,
                "technician_id": tech_options[selected_tech],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            })
            st.success(f"Task added: {description}")
            st.session_state["task_desc"] = ""

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
    sel = st.selectbox("Select task to mark done", options=list(options.keys()), key="task_done_sel")

    if st.button("Mark as Done"):
        task_id = options[sel]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                st.success(f"Task ID {task_id} marked done.")
                break

def update_task_ui():
    st.subheader("Update Task Description")
    tasks = st.session_state.tasks

    if not tasks:
        st.write("No tasks yet.")
        return

    options = {f"ID {t['id']}: {t['description']}": t["id"] for t in tasks}
    sel = st.selectbox("Select task to update", options=list(options.keys()), key="task_update_sel")
    new_desc = st.text_input("New description", key="task_update_desc")

    if st.button("Update Task"):
        if not new_desc.strip():
            st.warning("Description can’t be empty.")
        else:
            task_id = options[sel]
            for t in tasks:
                if t["id"] == task_id:
                    t["description"] = new_desc.strip()
                    st.success(f"Task ID {task_id} updated.")
                    st.session_state["task_update_desc"] = ""
                    break

def delete_task_ui():
    st.subheader("Delete Task")
    tasks = st.session_state.tasks

    if not tasks:
        st.write("No tasks to delete.")
        return

    options = {f"ID {t['id']}: {t['description']}": t["id"] for t in tasks}
    sel = st.selectbox("Select task to delete", options=list(options.keys()), key="task_delete_sel")

    if st.button("Delete Task"):
        task_id = options[sel]
        st.session_state.tasks = [t for t in tasks if t["id"] != task_id]
        st.success(f"Task ID {task_id} deleted.")

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

# ----------------------------
# Main Application
# ----------------------------

def main():
    st.title("🛠️ Service Tracker")

    menu = [
        "Home",
        "Add Technician",
        "List Technicians",
        "Add Task",
        "List Tasks",
        "Mark Task Done",
        "Update Task",
        "Delete Task",
        "Report Last 30 Days",
        "Import/Export"
    ]

    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "Home"

    st.sidebar.title("📋 Menu")
    for item in menu:
        if st.sidebar.button(item):
            st.session_state.selected_menu = item

    choice = st.session_state.selected_menu
    st.subheader(choice)

    if choice == "Home":
        st.write("Welcome to the Service Tracker App!")
    elif choice == "Add Technician":
        add_technician_ui()
    elif choice == "List Technicians":
        list_technicians_ui()
    elif choice == "Add Task":
        add_task_ui()
    elif choice == "List Tasks":
        st.checkbox("Show all (including done)", value=True, key="show_all_tasks")
        show_all = st.session_state.get("show_all_tasks", True)
        list_tasks_ui(show_all=show_all)
    elif choice == "Mark Task Done":
        mark_task_done_ui()
    elif choice == "Update Task":
        update_task_ui()
    elif choice == "Delete Task":
        delete_task_ui()
    elif choice == "Report Last 30 Days":
        report_ui()
    elif choice == "Import/Export":
        st.write("## Import Technicians")
        import_tech_file()
        st.write("## Export Technicians")
        export_tech_file()
    else:
        st.write("Unknown option.")

# ----------------------------
# Run the App
# ----------------------------

if __name__ == "__main__":
    main()
