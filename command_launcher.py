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

def list_descriptions():
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    print("\nCommand Descriptions:")
    for idx, c in enumerate(commands, 1):
        print(f"{idx}. {c['description']}")

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

def run_last_command():
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    last_command = commands[-1]
    print(f"\nRunning last command: {last_command['description']} [{last_command['command']}]\n")
    subprocess.run(last_command['command'], shell=True)

def main():
    while True:
        print("\nCommand Launcher Menu:")
        print("1. Add command (a)")
        print("2. List commands (ls)")
        print("3. Run command (r)")
        print("4. Run last command (l)")
        print("5. List command descriptions (ld)")
        print("6. Exit (e)")
        print("\nShortcuts:")
        print("  a  - Add command")
        print("  ls - List commands")
        print("  ld - List command descriptions")
        print("  l  - Run last command")
        print("  r  - Run command")
        print("  e  - Exit")
        
        choice = input("\nChoose an option: ").strip().lower()
        
        if choice in ["1", "add", "a"]:
            add_command()
        elif choice in ["2", "ls"]:
            list_commands()
        elif choice in ["3", "r"]:
            run_command()
        elif choice in ["4", "l"]:
            run_last_command()
        elif choice in ["5", "ld"]:
            list_descriptions()
        elif choice in ["6", "exit", "quit", "e"]:
            break
        else:
            print("Invalid choice. Use numbers or shortcuts (a, ls, ld, l, r, e).")

if __name__ == "__main__":
    main() 