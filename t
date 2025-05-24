#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set PYTHONPATH to include the current directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Function to display the menu
show_menu() {
    clear
    echo -e "${YELLOW}Salesforce Sync Test Runner${NC}"
    echo "====================================="
    echo "1) Run All Tests"
    echo "2) Account Creation Test"
    echo "3) Account Search Test"
    echo "4) File Upload Test"
    echo "5) File Download Test"
    echo "6) Account Deletion Test"
    echo "7) Account Query and Filter Test"
    echo "8) Toggle Debug Mode (Currently: ${DEBUG_MODE:-OFF})"
    echo "9) Exit"
    echo "====================================="
    echo -n "Enter your choice (1-9): "
}

# Function to run the selected test
run_test() {
    local test_option=$1
    echo -e "\n${YELLOW}Running test: $test_option${NC}"
    echo "-------------------------------------"
    
    # Build the command with debug flag if enabled
    local cmd="python3 test_sync.py --test \"$test_option\""
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
    
    case $choice in
        1)
            run_test "all"
            ;;
        2)
            run_test "account-creation"
            ;;
        3)
            run_test "account-search"
            ;;
        4)
            run_test "file-upload"
            ;;
        5)
            run_test "file-download"
            ;;
        6)
            run_test "account-deletion"
            ;;
        7)
            run_test "account-query"
            ;;
        8)
            toggle_debug
            ;;
        9)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done 