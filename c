#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set PYTHONPATH to include the src directory
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Function to display the menu
show_menu() {
    clear
    echo -e "${YELLOW}Salesforce Sync Command Runner${NC}"
    echo "====================================="
    echo "1) (a) Add Command"
    echo "2) (ls) List Commands"
    echo "3) (ld) List Commands with Description"
    echo "4) (l) Run Last Command"
    echo "5) (r) Run Command"
    echo "6) (q) Quit"
    echo "====================================="
    echo -n "Enter your choice (number or shortcut): "
}

# Function to add a new command
add_command() {
    echo -e "\n${YELLOW}Add New Command${NC}"
    echo "-------------------------------------"
    echo -n "Enter command description: "
    read description
    echo -n "Enter command: "
    read command
    
    # Add the command to commands.json
    python3 -c "
import json
import os

commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
else:
    commands = []

commands.append({
    'description': '$description',
    'command': '$command'
})

with open(commands_file, 'w') as f:
    json.dump(commands, f, indent=2)
"
    echo -e "\n${GREEN}Command added successfully!${NC}"
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to list all commands
list_commands() {
    echo -e "\n${YELLOW}Saved Commands${NC}"
    echo "-------------------------------------"
    python3 -c "
import json
import os

commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    for i, cmd in enumerate(commands, 1):
        print(f'{i}) {cmd[\"description\"]}')
else:
    print('No commands saved yet.')
"
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to list commands with description
list_commands_with_description() {
    echo -e "\n${YELLOW}Saved Commands with Description${NC}"
    echo "-------------------------------------"
    python3 -c "
import json
import os

commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    for i, cmd in enumerate(commands, 1):
        print(f'{i}) {cmd[\"description\"]}')
        print(f'   Command: {cmd[\"command\"]}')
        print()
else:
    print('No commands saved yet.')
"
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to run last command
run_last_command() {
    echo -e "\n${YELLOW}Running Last Command${NC}"
    echo "-------------------------------------"
    
    # Get the last command from commands.json
    cmd=$(python3 -c "
import json
import os
import sys

commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    if commands:
        print(commands[-1]['command'])
    else:
        print('No commands saved yet.', file=sys.stderr)
        sys.exit(1)
else:
    print('No commands saved yet.', file=sys.stderr)
    sys.exit(1)
")
    
    if [ $? -eq 0 ]; then
        echo -e "\n${YELLOW}Running command: $cmd${NC}"
        echo "-------------------------------------"
        eval $cmd
        exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo -e "\n${GREEN}Command completed successfully!${NC}"
        else
            echo -e "\n${RED}Command failed!${NC}"
        fi
    else
        echo -e "\n${RED}Error: No commands saved yet${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to run a command
run_command() {
    local cmd_num="$1"
    
    # If no argument provided, prompt for command number
    if [ -z "$cmd_num" ]; then
        echo -e "\n${YELLOW}Run Command${NC}"
        echo "-------------------------------------"
        echo -n "Enter command number: "
        read cmd_num
    fi
    
    # Get the command from commands.json
    cmd=$(python3 -c "
import json
import os
import sys

commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    try:
        cmd = commands[int('$cmd_num') - 1]['command']
        print(cmd)
    except (IndexError, ValueError):
        print('Invalid command number', file=sys.stderr)
        sys.exit(1)
else:
    print('No commands saved yet.', file=sys.stderr)
    sys.exit(1)
")
    
    if [ $? -eq 0 ]; then
        echo -e "\n${YELLOW}Running command: $cmd${NC}"
        echo "-------------------------------------"
        eval $cmd
        exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo -e "\n${GREEN}Command completed successfully!${NC}"
        else
            echo -e "\n${RED}Command failed!${NC}"
        fi
    else
        echo -e "\n${RED}Error: Invalid command number${NC}"
    fi
    
    # Only show the "Press Enter to continue" prompt if we're in interactive mode
    if [ -z "$1" ]; then
        echo "-------------------------------------"
        echo -n "Press Enter to continue..."
        read
    fi
}

# Main loop
while true; do
    show_menu
    read -r choice arg  # Read both choice and potential argument
    
    # Convert choice to lowercase
    choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')
    
    # If choice is 'r' or '5' and an argument was provided, run the command
    if [[ $choice =~ ^[5r]$ ]] && [ ! -z "$arg" ]; then
        run_command "$arg"
        continue
    fi
    
    case $choice in
        1|a)
            add_command
            ;;
        2|ls)
            list_commands
            ;;
        3|ld)
            list_commands_with_description
            ;;
        4|l)
            run_last_command
            ;;
        5|r)
            run_command
            ;;
        6|q)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done 