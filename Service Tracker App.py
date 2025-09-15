import streamlit as st
import json
import os
from datetime import datetime, timedelta
import subprocess
import platform

# Config
SYNCED_FOLDER = r"C:\Users\Ia\OneDrive - Eltronic Group A S\chwe tracker app files"
TECH_FILE = os.path.join(SYNCED_FOLDER, "tech.json")

# Ensure folder exists
def ensure_synced_folder():
    os.makedirs(SYNCED_FOLDER, exist_ok=True)

# Ensure tech file exists
def ensure_tech_file():
    if not os.path.exists(TECH_FILE):
        with open(TECH_FILE, "w") as f:
            json.dump([], f)

# Load technicians from disk
def load_tech_from_disk():
    try:
        with open(TECH_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        st.error(f"Failed to load technician list: {e}")
        return []

# Save technicians to disk
def save_tech_to_disk(tech_list):
    ensure_synced_folder()
    with open(TECH_FILE, "w") as f:
        json.dump(tech_list, f, indent=4)

# Get tech name by id
def get_technician_name(technicians, tech_id):
    for t in technicians:
        if t["id"] == tech_id:
            return t["name"]
    return "Unknown"

# UI: Add technician
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

            save_tech_to_disk(techs)
            st.session_state.tech = techs

            # Clear inputs
            st.session_state["tech_name"] = ""
            st.session_state["tech_phone"] = ""
            st.session_state["tech_email"] = ""

# UI: List technicians
def list_technicians_ui():
    st.subheader("Technicians")
    techs = st.session_state.tech
    if not techs:
        st.write("No technicians yet.")
    else:
        for t in techs:
            st.write(f"ID {t['id']}: {t['name']} | Phone: {t['phone']} | Email: {t['email']}")

# UI: Add task
def add_task_ui():
    st.subheader("Add Task")
    techs = st.session_state.tech
    if not techs:
        st.warning("Add a technician first.")
        return

    tasks = st.session_state.tasks

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
            st.success(f"Task added: {description.strip()}")
            st.session_state["task_desc"] = ""

# UI: List tasks
def list_tasks_ui(show_all=True):
    st.subheader("Tasks")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
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

# UI: Mark task done
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

# UI: Update task description
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

# UI: Delete task
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
        tasks[:] = [t for t in tasks if t["id"] != task_id]
        st.success(f"Task ID {task_id} deleted.")

# UI: Report last 30 days tasks
def report_ui():
    st.subheader("Report: Tasks Completed in Last 30 Days")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
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

# UI: Import technicians
def import_technicians_ui():
    st.subheader("Import Technicians JSON")
    uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                save_tech_to_disk(data)
                st.session_state.tech = data
                st.success("Technicians imported successfully.")
            else:
                st.error("Uploaded file is not a list of technicians.")
        except Exception as e:
            st.error(f"Failed to import: {e}")

# UI: Export technicians
def export_technicians_ui():
    st.subheader("Export Technicians JSON")
    techs = st.session_state.tech
    if techs:
        st.download_button("Download technicians JSON", json.dumps(techs, indent=4), file_name="tech.json")
    else:
        st.write("No technicians to export.")

# Detect files in folder
def list_files_in_folder(folder):
    try:
        return sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
    except Exception as e:
        st.error(f"Failed to list files: {e}")
        return []

# Helper to open folder cross-platform
def open_folder(path):
    system_platform = platform.system()
    # Optional debug message - comment out or remove in production
    # st.write(f"Detected OS: {system_platform}")
    try:
        if system_platform == "Windows":
            os.startfile(path)
            st.success(f"Opened folder in Explorer: {path}")
        elif system_platform == "Darwin":  # macOS
            subprocess.run(["open", path])
            st.success(f"Opened folder in Finder: {path}")
        elif system_platform == "Linux":
            try:
                subprocess.run(["xdg-open", path])
                st.success(f"Opened folder in File Manager: {path}")
            except FileNotFoundError:
                st.warning(f"'xdg-open' not found. Please open the folder manually: {path}")
        else:
            st.warning(f"Opening folders not supported on {system_platform}. Please open manually: {path}")
    except Exception as e:
        st.error(f"Failed to open folder: {e}")

# MAIN FUNCTION
def main():
    st.title("Service Tracker")

    ensure_synced_folder()
    ensure_tech_file()

    if "tech" not in st.session_state:
        st.session_state.tech = load_tech_from_disk()

    if "tasks" not in st.session_state:
        st.session_state.tasks = []

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
        "Import Technicians",
        "Export Technicians"
    ]

    if "selected_menu" not in st.session_state:
        st.session_state.selected_menu = "Home"

    st.sidebar.title("Menu")
    selected = st.sidebar.radio("Navigate", menu, index=menu.index(st.session_state.selected_menu))
    st.session_state.selected_menu = selected

    choice = st.session_state.selected_menu
    st.subheader(choice)

    if choice == "Home":
        st.write("Welcome to the Service Tracker App!")
        st.markdown("### Files in Synced Folder")

        if st.button("Open Synced Folder in Explorer"):
            if os.path.exists(SYNCED_FOLDER):
                open_folder(SYNCED_FOLDER)
            else:
                st.error(f"Folder does not exist: {SYNCED_FOLDER}")

        files = list_files_in_folder(SYNCED_FOLDER)
        if not files:
            st.info("No files found in the synced folder.")
        else:
            for file in files:
                file_path = os.path.join(SYNCED_FOLDER, file)
                with open(file_path, "rb") as f:
                    st.download_button(label=f"Download {file}", data=f, file_name=file)

    elif choice == "Add Technician":
        add_technician_ui()
    elif choice == "List Technicians":
        list_technicians_ui()
    elif choice == "Add Task":
        add_task_ui()
    elif choice == "List Tasks":
        show_all = st.checkbox("Show all (including done)", value=True, key="show_all_tasks")
        list_tasks_ui(show_all=show_all)
    elif choice == "Mark Task Done":
        mark_task_done_ui()
    elif choice == "Update Task":
        update_task_ui()
    elif choice == "Delete Task":
        delete_task_ui()
    elif choice == "Report Last 30 Days":
        report_ui()
    elif choice == "Import Technicians":
        import_technicians_ui()
    elif choice == "Export Technicians":
        export_technicians_ui()
    else:
        st.write("Unknown option.")

if __name__ == "__main__":
    main()
