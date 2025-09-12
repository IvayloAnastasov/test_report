import streamlit as st
import json
import os
from datetime import datetime, timedelta

DATA_DIR = "data"
TECHNICIANS_FILE = os.path.join(DATA_DIR, "technicians.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TECHNICIANS_FILE):
        with open(TECHNICIANS_FILE, "w") as f:
            json.dump([], f)
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w") as f:
            json.dump([], f)

def load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

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
            techs = load_json(TECHNICIANS_FILE)
            new_id = 1 + max([t["id"] for t in techs], default=0)
            techs.append({
                "id": new_id,
                "name": name.strip(),
                "phone": phone.strip(),
                "email": email.strip()
            })
            save_json(TECHNICIANS_FILE, techs)
            st.success(f"Added technician {name}")
            # Clear inputs
            st.session_state["tech_name"] = ""
            st.session_state["tech_phone"] = ""
            st.session_state["tech_email"] = ""

def list_technicians_ui():
    st.subheader("Technicians")
    techs = load_json(TECHNICIANS_FILE)
    if not techs:
        st.write("No technicians yet.")
    else:
        for t in techs:
            st.write(f"ID {t['id']}: {t['name']} | Phone: {t['phone']} | Email: {t['email']}")

def add_task_ui():
    st.subheader("Add Task")
    techs = load_json(TECHNICIANS_FILE)
    if not techs:
        st.warning("Add a technician first.")
        return
    tasks = load_json(TASKS_FILE)

    # Technician selection
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
            save_json(TASKS_FILE, tasks)
            st.success(f"Task added: {description}")
            st.session_state["task_desc"] = ""

def list_tasks_ui(show_all=True):
    st.subheader("Tasks")
    tasks = load_json(TASKS_FILE)
    techs = load_json(TECHNICIANS_FILE)
    if not tasks:
        st.write("No tasks yet.")
        return
    for task in tasks:
        if (not show_all) and task["done"]:
            continue
        status = "✅ Done" if task["done"] else "❗ Pending"
        tech_name = get_technician_name(techs, task["technician_id"])
        created = datetime.fromisoformat(task["created_at"]).strftime("%Y-%m-%d")
        line = f"ID {task['id']}: {task['description']} (Tech: {tech_name}) — Created: {created} — Status: {status}"
        st.write(line)

def mark_task_done_ui():
    st.subheader("Mark Task as Done")
    tasks = load_json(TASKS_FILE)
    pending_tasks = [t for t in tasks if not t["done"]]
    if not pending_tasks:
        st.write("No pending tasks.")
        return
    options = { f"ID {t['id']}: {t['description']}" : t["id"] for t in pending_tasks }
    sel = st.selectbox("Select task to mark done", options=list(options.keys()), key="task_done_sel")
    if st.button("Mark as Done"):
        task_id = options[sel]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                save_json(TASKS_FILE, tasks)
                st.success(f"Task ID {task_id} marked done.")
                break

def update_task_ui():
    st.subheader("Update Task Description")
    tasks = load_json(TASKS_FILE)
    if not tasks:
        st.write("No tasks yet.")
        return
    options = { f"ID {t['id']}: {t['description']}" : t["id"] for t in tasks }
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
                    save_json(TASKS_FILE, tasks)
                    st.success(f"Task ID {task_id} updated.")
                    st.session_state["task_update_desc"] = ""
                    break

def delete_task_ui():
    st.subheader("Delete Task")
    tasks = load_json(TASKS_FILE)
    if not tasks:
        st.write("No tasks to delete.")
        return
    options = { f"ID {t['id']}: {t['description']}" : t["id"] for t in tasks }
    sel = st.selectbox("Select task to delete", options=list(options.keys()), key="task_delete_sel")
    if st.button("Delete Task"):
        task_id = options[sel]
        tasks = [t for t in tasks if t["id"] != task_id]
        save_json(TASKS_FILE, tasks)
        st.success(f"Task ID {task_id} deleted.")

def report_ui():
    st.subheader("Report: Tasks Completed in Last 30 Days")
    tasks = load_json(TASKS_FILE)
    techs = load_json(TECHNICIANS_FILE)
    cutoff = datetime.now() - timedelta(days=30)
    done_tasks = []
    for t in tasks:
        if t["done"] and t.get("completed_at"):
            comp = datetime.fromisoformat(t["completed_at"])
            if comp >= cutoff:
                done_tasks.append(t)
    if not done_tasks:
        st.write("No tasks completed in last 30 days.")
    else:
        for t in done_tasks:
            tech_name = get_technician_name(techs, t["technician_id"])
            comp = datetime.fromisoformat(t["completed_at"]).strftime("%Y-%m-%d")
            st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Completed: {comp}")

def main():
    st.title("Service Tracker")
    ensure_data_files()

    # Define menu options
    menu = [
        "Home",
        "Add Technician",
        "List Technicians",
        "Add Task",
        "List Tasks",
        "Mark Task Done",
        "Update Task",
        "Delete Task",
        "Report Last 30 Days"
    ]

    # Initialize session state for menu
    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "Home"

    # Sidebar buttons
    st.sidebar.title("Menu")
    for item in menu:
        if st.sidebar.button(item):
            st.session_state.selected_menu = item

    # Display corresponding screen
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
    else:
        st.write("Unknown option.")

    main()

