#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Set PYTHONPATH to include the src directory
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Variable to store the last command
LAST_COMMAND=""

# Function to display the menu
show_menu() {
    clear
    echo -e "${CYAN}Database Management Tool${NC}"
    echo "====================================="
    echo -e "${YELLOW}📊 Database Inspection:${NC}"
    echo "1) (c) Check Supabase Contents"
    echo "2) (t) Test Supabase Connection"
    echo "3) (i) Test Integration"
    echo "4) (s) Test Separated Approach"
    echo "5) (sa) Search Dropbox Accounts"
    echo ""
    echo -e "${YELLOW}🗑️  Data Management:${NC}"
    echo "6) (cl) Clear Database Data"
    echo "7) (fc) Force Clear Database"
    echo "8) (r) Reset Database (Complete)"
    echo "9) (rs) Reset Database (Simple)"
    echo ""
    echo -e "${YELLOW}🏗️  Schema Management:${NC}"
    echo "10) (cs) Create New Schema"
    echo "11) (ct) Create Tables via REST"
    echo "12) (m) Migrate Table Names"
    echo "13) (fa) Fix Supabase Auth"
    echo "14) (rl) Remove Legacy Tables"
    echo ""
    echo -e "${YELLOW}📋 Utilities:${NC}"
    echo "15) (v) View Schema Diagram"
    echo "16) (rd) Open Database README"
    echo "17) (gd) Generate Schema Diagram"
    echo "18) (l) Run Last Command"
    echo "19) (q) Quit"
    echo "====================================="
    echo -n "Enter your choice (number or shortcut): "
}

# Function to run a database script
run_script() {
    local script_name=$1
    local description=$2
    local script_path="database/scripts/$script_name"
    
    echo -e "\n${YELLOW}Running: $description${NC}"
    echo "-------------------------------------"
    
    # Check if script exists
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}Error: Script not found: $script_path${NC}"
        echo -n "Press Enter to continue..."
        read
        return
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Build the command
    local cmd="python3 $script_path 2>&1 | tee logs/database_${script_name%.*}.log"
    
    # Store the command
    LAST_COMMAND="$cmd"
    
    # Show the command being executed
    echo -e "${YELLOW}Executing command:${NC} $cmd"
    echo "-------------------------------------"
    
    # Run the script
    eval $cmd
    exit_code=$?
    
    # Check the exit code
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Operation completed successfully!${NC}"
    else
        echo -e "\n${RED}Operation failed!${NC}"
    fi
    
    # Show the command again at the end
    echo -e "\n${YELLOW}Command that was executed:${NC} $cmd"
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to view schema diagram
view_schema_diagram() {
    echo -e "\n${YELLOW}Opening Schema Diagram${NC}"
    echo "-------------------------------------"
    
    local diagram_path="database/diagrams/database_schema_diagram.html"
    
    if [ ! -f "$diagram_path" ]; then
        echo -e "${RED}Error: Schema diagram not found: $diagram_path${NC}"
        echo -n "Press Enter to continue..."
        read
        return
    fi
    
    echo -e "${GREEN}Opening schema diagram in browser...${NC}"
    
    # Try to open the file with the default browser
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "$diagram_path"
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open "$diagram_path"
    elif command -v start >/dev/null 2>&1; then
        # Windows
        start "$diagram_path"
    else
        echo -e "${YELLOW}Could not open browser automatically.${NC}"
        echo -e "${YELLOW}Please open this file manually:${NC} $diagram_path"
    fi
    
    echo -e "${GREEN}Schema diagram opened!${NC}"
    echo -n "Press Enter to continue..."
    read
}

# Function to open database README
open_database_readme() {
    echo -e "\n${YELLOW}Opening Database README${NC}"
    echo "-------------------------------------"
    
    local readme_path="database/README.md"
    
    if [ ! -f "$readme_path" ]; then
        echo -e "${RED}Error: Database README not found: $readme_path${NC}"
        echo -n "Press Enter to continue..."
        read
        return
    fi
    
    echo -e "${GREEN}Opening database README...${NC}"
    
    # Try to open the file with the default text editor
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "$readme_path"
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open "$readme_path"
    elif command -v start >/dev/null 2>&1; then
        # Windows
        start "$readme_path"
    else
        echo -e "${YELLOW}Could not open file automatically.${NC}"
        echo -e "${YELLOW}Please open this file manually:${NC} $readme_path"
    fi
    
    echo -e "${GREEN}Database README opened!${NC}"
    echo -n "Press Enter to continue..."
    read
}

# Function to run the last command
run_last_command() {
    if [ -z "$LAST_COMMAND" ]; then
        echo -e "\n${RED}No previous command available${NC}"
        sleep 2
        return
    fi
    
    echo -e "\n${YELLOW}Running last command:${NC}"
    echo "-------------------------------------"
    echo -e "${YELLOW}Executing command:${NC} $LAST_COMMAND"
    echo "-------------------------------------"
    
    eval $LAST_COMMAND
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Operation completed successfully!${NC}"
    else
        echo -e "\n${RED}Operation failed!${NC}"
    fi
    
    # Show the command again at the end
    echo -e "\n${YELLOW}Command that was executed:${NC} $LAST_COMMAND"
    echo "-------------------------------------"
    echo -n "Press Enter to continue..."
    read
}

# Function to show database status
show_status() {
    echo -e "\n${YELLOW}Database Status${NC}"
    echo "-------------------------------------"
    
    # Check if Supabase is running
    if docker ps | grep -q supabase; then
        echo -e "${GREEN}✅ Supabase is running${NC}"
    else
        echo -e "${RED}❌ Supabase is not running${NC}"
    fi
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ .env file exists${NC}"
    else
        echo -e "${RED}❌ .env file not found${NC}"
    fi
    
    # Check if database scripts directory exists
    if [ -d "database/scripts" ]; then
        echo -e "${GREEN}✅ Database scripts directory exists${NC}"
        echo -e "${BLUE}📁 Found $(ls database/scripts/*.py | wc -l | tr -d ' ') database scripts${NC}"
    else
        echo -e "${RED}❌ Database scripts directory not found${NC}"
    fi
    
    echo -n "Press Enter to continue..."
    read
}

# Main loop
while true; do
    show_menu
    read choice
    choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')  # Convert to lowercase
    
    case $choice in
        1|c)
            run_script "check_supabase_contents.py" "Check Supabase Contents"
            ;;
        2|t)
            run_script "test_supabase_check.py" "Test Supabase Connection"
            ;;
        3|i)
            run_script "test_integration.py" "Test Integration"
            ;;
        4|s)
            run_script "test_separated_approach.py" "Test Separated Approach"
            ;;
        5|sa)
            run_script "search_dropbox_accounts.py" "Search Dropbox Accounts"
            ;;
        6|cl)
            run_script "clear_database_data.py" "Clear Database Data"
            ;;
        7|fc)
            run_script "force_clear_database.py" "Force Clear Database"
            ;;
        8|r)
            run_script "reset_database.py" "Reset Database (Complete)"
            ;;
        9|rs)
            run_script "reset_database_simple.py" "Reset Database (Simple)"
            ;;
        10|cs)
            run_script "create_new_schema.py" "Create New Schema"
            ;;
        11|ct)
            run_script "create_tables_via_rest.py" "Create Tables via REST"
            ;;
        12|m)
            run_script "migrate_table_names.py" "Migrate Table Names"
            ;;
        13|fa)
            run_script "fix_supabase_auth.py" "Fix Supabase Auth"
            ;;
        14|rl)
            run_script "remove_legacy_tables.py" "Remove Legacy Tables"
            ;;
        15|v)
            view_schema_diagram
            ;;
        16|rd)
            open_database_readme
            ;;
        17|gd)
            run_script "generate_schema_diagram.py" "Generate Schema Diagram"
            ;;
        18|l)
            run_last_command
            ;;
        19|q)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            ;;
    esac
done 