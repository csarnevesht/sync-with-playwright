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
    echo -e "${YELLOW}Salesforce Sync Test Runner${NC}"
    echo "====================================="
    echo "1) (a) Run All Tests"
    echo "2) (c) Account Creation Test"
    echo "3) (s) Account Search Test"
    echo "4) (u) File Upload Test"
    echo "5) (d) Account Deletion Test"
    echo "6) (f) Account Filter Test"
    echo "7) (r) Account File Retrieval Test (and Scrolling)"
    echo "8) (x) Account File Deletion Test"
    echo "9) (t) Toggle Debug Mode (Currently: ${DEBUG_MODE:-OFF})"
    echo "10) (q) Quit"
    echo "====================================="
    echo -n "Enter your choice (number or shortcut): "
}

# Function to run the selected test
run_test() {
    local test_option=$1
    echo -e "\n${YELLOW}Running test: $test_option${NC}"
    echo "-------------------------------------"
    
    # Build the command with debug flag if enabled
    local cmd="python3 src/test_sync.py --test \"$test_option\""
    if [ "$DEBUG_MODE" = "ON" ]; then
        cmd="$cmd --debug"
    fi
    
    # Run the test without capturing output to allow real-time logging
    eval $cmd
    exit_code=$?
    
    # Check the exit code
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Test completed successfully!${NC}"
    else
        echo -e "\n${RED}Test failed!${NC}"
    fi
    
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to toggle debug mode
toggle_debug() {
    if [ "$DEBUG_MODE" = "ON" ]; then
        DEBUG_MODE="OFF"
        echo -e "\n${YELLOW}Debug mode disabled${NC}"
    else
        DEBUG_MODE="ON"
        echo -e "\n${YELLOW}Debug mode enabled${NC}"
    fi
    sleep 1
}

# Main loop
while true; do
    show_menu
    read choice
    choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')  # Convert to lowercase
    
    case $choice in
        1|a)
            run_test "all"
            ;;
        2|c)
            run_test "account-creation"
            ;;
        3|s)
            run_test "account-search"
            ;;
        4|u)
            run_test "file-upload"
            ;;
        5|d)
            run_test "account-deletion"
            ;;
        6|f)
            run_test "account-filter"
            ;;
        7|r)
            run_test "account-file-retrieval"
            ;;
        8|x)
            run_test "account-file-deletion"
            ;;
        9|t)
            toggle_debug
            ;;
        10|q)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done 