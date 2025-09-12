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


# Utility Functions
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# Technician Management
def add_technician():
    technicians = load_json(TECHNICIANS_FILE)
    name = input("Enter technician name: ")
    phone = input("Enter phone number: ")
    email = input("Enter email address: ")

    technicians.append({
        "id": len(technicians) + 1,
        "name": name,
        "phone": phone,
        "email": email
    })

    save_json(TECHNICIANS_FILE, technicians)
    print("Technician added.")


def list_technicians():
    technicians = load_json(TECHNICIANS_FILE)
    for tech in technicians:
        print(f"{tech['id']}: {tech['name']} | {tech['phone']} | {tech['email']}")


# Task Management
def add_task():
    tasks = load_json(TASKS_FILE)
    list_technicians()
    tech_id = int(input("Assign to technician (enter ID): "))
    description = input("Enter task description: ")

    tasks.append({
        "id": len(tasks) + 1,
        "technician_id": tech_id,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "done": False,
        "completed_at": None
    })

    save_json(TASKS_FILE, tasks)
    print("Task added.")


def list_tasks(show_all=True):
    tasks = load_json(TASKS_FILE)
    technicians = {t["id"]: t["name"] for t in load_json(TECHNICIANS_FILE)}
    for task in tasks:
        if not show_all and task["done"]:
            continue
        status = "Done" if task["done"] else "Pending"
        tech_name = technicians.get(task["technician_id"], "Unknown")
        print(f"{task['id']}: [{status}] {task['description']} (Tech: {tech_name})")


def mark_task_done():
    list_tasks(show_all=False)
    task_id = int(input("Enter task ID to mark as done: "))
    tasks = load_json(TASKS_FILE)

    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            task["completed_at"] = datetime.now().isoformat()
            save_json(TASKS_FILE, tasks)
            print("Task marked as done.")
            return

    print("Task not found.")


def delete_task():
    list_tasks()
    task_id = int(input("Enter task ID to delete: "))
    tasks = load_json(TASKS_FILE)
    tasks = [task for task in tasks if task["id"] != task_id]
    save_json(TASKS_FILE, tasks)
    print("Task deleted.")


def update_task():
    list_tasks()
    task_id = int(input("Enter task ID to update: "))
    tasks = load_json(TASKS_FILE)

    for task in tasks:
        if task["id"] == task_id:
            new_desc = input(f"Enter new description (leave empty to keep '{task['description']}'): ")
            if new_desc.strip():
                task["description"] = new_desc.strip()
            save_json(TASKS_FILE, tasks)
            print("Task updated.")
            return

    print("Task not found.")


# Reporting
def task_report_last_30_days():
    tasks = load_json(TASKS_FILE)
    technicians = {t["id"]: t["name"] for t in load_json(TECHNICIANS_FILE)}
    cutoff = datetime.now() - timedelta(days=30)

    print("\nTasks Completed in Last 30 Days:")
    print("-" * 40)
    for task in tasks:
        if task["done"] and task["completed_at"]:
            completed_at = datetime.fromisoformat(task["completed_at"])
            if completed_at >= cutoff:
                tech_name = technicians.get(task["technician_id"], "Unknown")
                print(f"{task['id']}: {task['description']} | Completed by: {tech_name} on {completed_at.date()}")


# Main Menu
def main():
    ensure_data_files()
    while True:
        print("\nService Tracker Menu:")
        print("1. Add Technician")
        print("2. List Technicians")
        print("3. Add Task")
        print("4. List Tasks")
        print("5. Update Task")
        print("6. Delete Task")
        print("7. Mark Task as Done")
        print("8. Task Report (Last 30 Days)")
        print("0. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            add_technician()
        elif choice == "2":
            list_technicians()
        elif choice == "3":
            add_task()
        elif choice == "4":
            list_tasks()
        elif choice == "5":
            update_task()
        elif choice == "6":
            delete_task()
        elif choice == "7":
            mark_task_done()
        elif choice == "8":
            task_report_last_30_days()
        elif choice == "0":
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
