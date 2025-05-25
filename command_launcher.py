import json
import subprocess
import os

COMMANDS_FILE = "commands.json"

def load_commands():
    if not os.path.exists(COMMANDS_FILE):
        return []
    with open(COMMANDS_FILE, "r") as f:
        return json.load(f)

def save_commands(commands):
    with open(COMMANDS_FILE, "w") as f:
        json.dump(commands, f, indent=2)

def add_command():
    print("\nAdd a new command:")
    desc = input("Enter description: ").strip()
    cmd = input("Enter command: ").strip()
    commands = load_commands()
    commands.append({"description": desc, "command": cmd})
    save_commands(commands)
    print("Command added.")

def list_commands():
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    print("\nSaved Commands:")
    for idx, c in enumerate(commands, 1):
        print(f"{idx}. {c['description']} [{c['command']}]")

def run_command():
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    list_commands()
    try:
        choice = int(input("Select a command to run (number): "))
        if 1 <= choice <= len(commands):
            print(f"\nRunning: {commands[choice-1]['command']}")
            subprocess.run(commands[choice-1]['command'], shell=True)
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input.")

def main():
    while True:
        print("\n1. Add command\n2. List commands\n3. Run command\n4. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_command()
        elif choice == "2":
            list_commands()
        elif choice == "3":
            run_command()
        elif choice == "4":
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main() 