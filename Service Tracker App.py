import streamlit as st
import json
from datetime import datetime, timedelta
import requests
import time
import jwt  # PyJWT must be installed

# ------------------ Configuration ------------------

SPREADSHEET_ID = "1tTjNIHuwQ0PcsfK2Si7IjLP_S0ZeJLmo7C1yMyGqw18"  # 🔧 spreadsheet ID from your link
SHEET_NAME = "Sheet1"  # 🔧 replace if your sheet tab has another name

SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ------------------ Auth: Service Account JWT Flow ------------------

def get_access_token():
    sa = st.secrets["google_service_account"]
    now = int(time.time())
    header = {
        "alg": "RS256",
        "typ": "JWT"
    }
    payload = {
        "iss": sa["client_email"],
        "scope": " ".join(SCOPES),
        "aud": sa["token_uri"],
        "iat": now,
        "exp": now + 3600
    }
    private_key = sa["private_key"]
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    token_resp = requests.post(sa["token_uri"], data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": encoded_jwt
    })
    if token_resp.status_code != 200:
        st.error(f"Error obtaining access token: {token_resp.text}")
        return None
    token_data = token_resp.json()
    return token_data.get("access_token")

# ------------------ Sheets API helpers ------------------

def sheets_get_values(range_a1, access_token):
    url = f"{SHEETS_BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        st.error(f"Sheets GET error: {resp.status_code} {resp.text}")
        return None
    return resp.json()

def sheets_append_values(range_a1, values, access_token):
    url = f"{SHEETS_BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}:append"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "valueInputOption": "USER_ENTERED",
        "insertDataOption": "INSERT_ROWS"
    }
    body = {"values": values}
    resp = requests.post(url, headers=headers, params=params, json=body)
    if resp.status_code not in (200, 201):
        st.error(f"Append error: {resp.status_code} {resp.text}")
    return resp.json()

def sheets_update_values(range_a1, values, access_token):
    url = f"{SHEETS_BASE_URL}/{SPREADSHEET_ID}/values/{range_a1}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "valueInputOption": "USER_ENTERED"
    }
    body = {"values": values}
    resp = requests.put(url, headers=headers, params=params, json=body)
    if resp.status_code != 200:
        st.error(f"Update error: {resp.status_code} {resp.text}")
    return resp.json()


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
        st.write("No technicians")
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
    description = st.text_input("Description", key="task_desc")

    if st.button("Add Task"):
        if not description.strip():
            st.warning("Description required.")
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
            st.success(f"Added task {description.strip()}")

            # Sync to Google Sheet: append
            access_token = get_access_token()
            if access_token:
                tech_name = get_technician_name(techs, task["technician_id"])
                values = [[
                    task["id"],
                    tech_name,
                    task["description"],
                    task["created_at"],
                    "Pending",
                    ""
                ]]
                sheets_append_values(f"{SHEET_NAME}!A1:F", values, access_token)

def list_tasks_ui(show_all=True):
    st.subheader("Tasks")
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    if not tasks:
        st.write("No tasks yet")
        return
    for t in tasks:
        if not show_all and t["done"]:
            continue
        tech_name = get_technician_name(techs, t["technician_id"])
        status = "✅ Done" if t["done"] else "❗ Pending"
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
    selection = st.selectbox("Select task", list(options.keys()), key="task_done_sel")
    if st.button("Mark Done"):
        task_id = options[selection]
        for t in tasks:
            if t["id"] == task_id:
                t["done"] = True
                t["completed_at"] = datetime.now().isoformat()
                access_token = get_access_token()
                if access_token:
                    # read the rows to find which row to update
                    resp = sheets_get_values(f"{SHEET_NAME}!A2:F", access_token)
                    if resp and "values" in resp:
                        rows = resp["values"]
                        for i, row in enumerate(rows, start=2):
                            if str(row[0]) == str(task_id):
                                values = [["Done", t["completed_at"]]]
                                sheets_update_values(f"{SHEET_NAME}!E{i}:F{i}", values, access_token)
                                break
                st.success(f"Task {task_id} marked done.")
                break

def report_ui():
    st.subheader("Tasks Completed in Last 30 Days")
    now = datetime.now()
    cutoff = now - timedelta(days=30)
    tasks = st.session_state.tasks
    techs = st.session_state.tech
    for t in tasks:
        if t["done"] and t.get("completed_at"):
            done_dt = datetime.fromisoformat(t["completed_at"])
            if done_dt >= cutoff:
                tech_name = get_technician_name(techs, t["technician_id"])
                st.write(f"ID {t['id']}: {t['description']} — Tech: {tech_name} — Completed: {done_dt.strftime('%Y-%m-%d')}")

def main():
    st.title("Service Tracker (Google Sheet sync)")

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

    choice = st.sidebar.radio("Menu", menu)
    st.subheader(choice)

    if choice == "Home":
        st.write("Welcome!")
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
