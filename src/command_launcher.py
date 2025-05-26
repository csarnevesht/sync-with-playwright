import json
import subprocess
import os
import sys
from pathlib import Path

# Get the directory where the script is located
SCRIPT_DIR = Path(__file__).parent
COMMANDS_FILE = SCRIPT_DIR / "commands.json"

def load_commands():
    if not COMMANDS_FILE.exists():
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
    print(f"[DEBUG] COMMANDS_FILE: {COMMANDS_FILE}")
    if COMMANDS_FILE.exists():
        with open(COMMANDS_FILE, 'r') as f:
            print("[DEBUG] commands.json contents:")
            print(f.read())
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    list_commands()
    try:
        choice = int(input("Select a command to run (number): "))
        if 1 <= choice <= len(commands):
            cmd = commands[choice-1]['command']
            print(f"\nRunning: {cmd}")
            
            # Set up environment variables
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"  # Force Python to be unbuffered
            env["PYTHONIOENCODING"] = "utf-8"  # Ensure proper encoding
            env["PYTHONPATH"] = str(SCRIPT_DIR.parent)  # Add parent directory to Python path
            
            print("Debug: Starting command execution...")
            print(f"Debug: Command: {cmd}")
            print(f"Debug: PYTHONPATH: {env['PYTHONPATH']}")
            
            # Run the command with shell=True
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                shell=True
            )
            
            # Stream the output in real-time
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    print(line)
                    output_lines.append(line)
            
            return_code = process.poll()
            print("Debug: Command completed successfully")
            print("Debug: Output:")
            print("\n".join(output_lines))
            print(f"Debug: Command exited with code: {return_code}")
            return return_code
                
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input.")
    except Exception as e:
        print(f"Error running command: {e}")
        import traceback
        traceback.print_exc()

def run_last_command():
    commands = load_commands()
    if not commands:
        print("No commands saved.")
        return
    last_command = commands[-1]
    print(f"\nRunning last command: {last_command['description']} [{last_command['command']}]\n")
    run_command()  # Reuse the run_command logic

def show_help():
    """Display help information about the command launcher."""
    print("\nCommand Launcher Help:")
    print("This tool helps you manage and run commands for the sync project.")
    print("\nMenu Options:")
    print("1. (a) Add command - Add a new command to the list")
    print("2. (ls) List commands - Show all saved commands")
    print("3. (r) Run command - Execute a saved command")
    print("4. (l) Run last command - Execute the most recently added command")
    print("5. (ld) List descriptions - Show command descriptions only")
    print("6. (e) Exit - Quit the program")
    print("\nShortcuts:")
    print("  a  - Add command")
    print("  ls - List commands")
    print("  ld - List command descriptions")
    print("  l  - Run last command")
    print("  r  - Run command")
    print("  h  - Show this help")
    print("  ?  - Show this help")
    print("  e  - Exit")

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
        print("  h  - Show help")
        print("  ?  - Show help")
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
        elif choice in ["h", "?", "help"]:
            show_help()
        else:
            print("Invalid choice. Use numbers or shortcuts (a, ls, ld, l, r, h, e).")

if __name__ == "__main__":
    main() 