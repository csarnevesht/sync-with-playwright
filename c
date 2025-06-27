#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}Virtual environment activated${NC}"
fi

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
    echo "6) (pg) Ping Dropbox and Salesforce"
    echo "7) (br) Start Browser with Salesforce"
    echo "8) (db) List Dropbox Accounts Only"
    echo "9) (cp) Copy Dropbox Account Folders to Salesforce (Preserve Dates)"
    echo "10) (an) Analyze Salesforce Account Data for All Dropbox Accounts"
    echo "11) (e) Extract and Store Dropbox Data for Account"
    echo "12) (h) Help - Show Python Script for Command"
    echo "13) (q) Quit"
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
    python -c "
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
    python -c "
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
    python -c "
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
    cmd=$(python -c "
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
    cmd=$(python -c "
import json
import os
import sys

cmd_num = '$cmd_num'
commands_file = 'src/commands.json'
if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    try:
        cmd = commands[int(cmd_num) - 1]['command']
        desc = commands[int(cmd_num) - 1]['description']
        print(f'Command {cmd_num}: {desc}')
        print(f'Python Script: {cmd}')
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

# Function to extract and store Dropbox data for account
extract_dropbox_data() {
    echo -e "\n${YELLOW}Extract and Store Dropbox Data for Account${NC}"
    echo "-------------------------------------"
    
    # Prompt for Dropbox account folder name
    echo -n "Enter Dropbox account folder name: "
    read dropbox_account_folder_name
    
    # Prompt for file filter with default value
    echo -n "Enter file filter [default '*']: "
    read file_filter
    
    # Use default value if empty
    if [ -z "$file_filter" ]; then
        file_filter="*"
    fi
    
    echo -e "\n${YELLOW}Running Dropbox extraction and analysis...${NC}"
    echo "-------------------------------------"
    
    # Run the main extraction command
    clear && python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info --continue-on-error --commands=extract-dropbox-account-app-files-info,store-in-supabase,analyze-account-data --dropbox-account-name="$dropbox_account_folder_name" --force-store-dropbox-info --file-filter "$file_filter"
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Dropbox extraction completed successfully!${NC}"
        echo -e "\n${YELLOW}Running database search...${NC}"
        
        # Run the database search command
        echo -e "1\n$dropbox_account_folder_name\n6" | python3 database/scripts/search_dropbox_accounts.py
        
        search_exit_code=$?
        
        if [ $search_exit_code -eq 0 ]; then
            echo -e "\n${GREEN}Database search completed successfully!${NC}"
        else
            echo -e "\n${RED}Database search failed!${NC}"
        fi
    else
        echo -e "\n${RED}Dropbox extraction failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to list Dropbox accounts only
list_dropbox_accounts_only() {
    echo -e "\n${YELLOW}Listing Dropbox Accounts Only${NC}"
    echo "-------------------------------------"
    
    echo -e "\n${YELLOW}Running Dropbox accounts listing...${NC}"
    echo "-------------------------------------"
    
    # Run the command to list Dropbox accounts only
    python -m sync.cmd_runner --dropbox-accounts-only
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Dropbox accounts listing completed successfully!${NC}"
    else
        echo -e "\n${RED}Dropbox accounts listing failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to copy Dropbox account folders to Salesforce accounts folder with preserved dates
copy_dropbox_account_folders() {
    echo -e "\n${YELLOW}Copy Dropbox Account Folders to Salesforce (Preserve Dates)${NC}"
    echo "-------------------------------------"
    
    echo -e "\n${YELLOW}Running Dropbox account folder copying with preserved dates...${NC}"
    echo "-------------------------------------"
    
    # Run the command to copy Dropbox account folders to Salesforce accounts folder with preserved dates
    clear && python -m sync.cmd_runner --dropbox-accounts --commands=copy-dropbox-account-files-preserve-dates --continue-on-error --keep
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Dropbox account folder copying completed successfully!${NC}"
    else
        echo -e "\n${RED}Dropbox account folder copying failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to start browser with Salesforce
start_browser_with_salesforce() {
    echo -e "\n${YELLOW}Start Browser with Salesforce${NC}"
    echo "-------------------------------------"
    
    echo -e "\n${YELLOW}Starting browser with Salesforce...${NC}"
    echo "-------------------------------------"
    
    # Run the command to start browser with Salesforce
    python -m cmd_start
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Browser started successfully!${NC}"
    else
        echo -e "\n${RED}Browser start failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to analyze Salesforce account data for all Dropbox accounts
analyze_salesforce_account_data() {
    echo -e "\n${YELLOW}Analyze Salesforce Account Data for All Dropbox Accounts${NC}"
    echo "-------------------------------------"
    
    echo -e "\n${YELLOW}Running Salesforce account data analysis for all Dropbox accounts...${NC}"
    echo "-------------------------------------"
    
    # Run the command to analyze Salesforce account data for all Dropbox accounts
    clear && python -m sync.cmd_runner --dropbox-accounts --dropbox-account-info --commands=extract-dropbox-account-app-files-info,analyze-account-data --salesforce-account-info --salesforce-accounts --continue-on-error --keep
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Salesforce account data analysis completed successfully!${NC}"
    else
        echo -e "\n${RED}Salesforce account data analysis failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to ping Dropbox and Salesforce
ping_dropbox_salesforce() {
    echo -e "\n${YELLOW}Ping Dropbox and Salesforce${NC}"
    echo "-------------------------------------"
    
    echo -e "\n${YELLOW}Running ping commands...${NC}"
    echo "-------------------------------------"
    
    # Run the command to ping Dropbox and Salesforce
    python -m sync.cmd_ping
    
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Ping commands completed successfully!${NC}"
    else
        echo -e "\n${RED}Ping commands failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to show help for a specific command
show_command_help() {
    local cmd_input="$1"
    
    # If no argument provided, prompt for command number or shortcut
    if [ -z "$cmd_input" ]; then
        echo -e "\n${YELLOW}Help - Show Python Script for Command${NC}"
        echo "-------------------------------------"
        echo -n "Enter command number or shortcut: "
        read cmd_input
    fi
    
    # Get the command from commands.json
    cmd=$(python -c "
import json
import os
import sys

cmd_input = '$cmd_input'
commands_file = 'src/commands.json'

# Define shortcut mappings
shortcuts = {
    'a': 1, 'ls': 2, 'ld': 3, 'l': 4, 'r': 5, 'pg': 6, 'br': 7, 'db': 8, 'cp': 9, 'an': 10, 'e': 11, 'h': 12, 'q': 13
}

if os.path.exists(commands_file):
    with open(commands_file, 'r') as f:
        commands = json.load(f)
    
    # Try to convert input to command number
    try:
        # If it's a number, use it directly
        if cmd_input.isdigit():
            cmd_num = int(cmd_input)
        # If it's a shortcut, look it up
        elif cmd_input in shortcuts:
            cmd_num = shortcuts[cmd_input]
        else:
            print(f'Invalid command number or shortcut: {cmd_input}', file=sys.stderr)
            sys.exit(1)
        
        # Get the command and description
        cmd = commands[cmd_num - 1]['command']
        desc = commands[cmd_num - 1]['description']
        print(f'Command {cmd_num} ({cmd_input}): {desc}')
        print(f'Python Script: {cmd}')
    except (IndexError, ValueError, KeyError):
        print(f'Invalid command number or shortcut: {cmd_input}', file=sys.stderr)
        sys.exit(1)
else:
    print('No commands saved yet.', file=sys.stderr)
    sys.exit(1)
")
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}Command Help:${NC}"
        echo "-------------------------------------"
        echo -e "$cmd"
        echo "-------------------------------------"
    else
        echo -e "\n${RED}Error: Invalid command number or shortcut${NC}"
    fi
    
    # Only show the "Press Enter to continue" prompt if we're in interactive mode
    if [ -z "$1" ]; then
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
    
    # Check for commands with arguments first
    if [ ! -z "$arg" ]; then
        # If choice is 'r' or '5' and an argument was provided, run the command
        if [[ $choice =~ ^(5|r)$ ]]; then
            run_command "$arg"
            continue
        fi
        
        # If choice is 'h' or '12' and an argument was provided, show help for that command
        if [[ $choice =~ ^(12|h)$ ]]; then
            show_command_help "$arg"
            continue
        fi
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
        6|pg)
            ping_dropbox_salesforce
            ;;
        7|br)
            start_browser_with_salesforce
            ;;
        8|db)
            list_dropbox_accounts_only
            ;;
        9|cp)
            copy_dropbox_account_folders
            ;;
        10|an)
            analyze_salesforce_account_data
            ;;
        11|e)
            extract_dropbox_data
            ;;
        12|h)
            show_command_help
            ;;
        13|q)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done 