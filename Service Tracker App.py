import streamlit as st
import json
import requests
from datetime import datetime, timedelta

# URL to tech.json on GitHub
GITHUB_TECH_URL = "https://raw.githubusercontent.com/yourusername/yourrepo/main/data/tech.json"  # Replace this!

def load_tech_from_github():
    try:
        response = requests.get(GITHUB_TECH_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load technicians from GitHub: {e}")
        return []

def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

def add_technician_ui():
    st.subheader("Add Technician")
    st.warning("Adding/editing technicians will not update GitHub. Read-only mode.")
    st.info("Edit tech.json directly in your GitHub repo to change data.")

def list_technicians_ui():
    st.subheader("Technicians")
    techs = st.session_state.tech
    if not techs:
        st.write("No technicians found.")
    else:
        for t in techs:
            st.write(f"ID {t['id']}: {t['name']} | Phone: {t['phone']} | Email: {t['email']}")

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
            tasks.append({
                "id": new_id,
                "technician_id": tech_options[selected_tech],
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "done": False,
                "completed_at": None
            })
            st.success(f"Task added: {description.strip()}")
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
    sel = st.selectbox("Select task to mark done", list(options.keys()), key="task_done_sel")
    if st.button("Mark as Done"):
        task_id = options[sel]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                st.success(f"Task ID {task_id} marked done.")
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
    st.title("Service Tracker")

    # Initialize state
    if "tech" not in st.session_state:
        st.session_state.tech = load_tech_from_github()
    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    menu = [
        "Home",
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
