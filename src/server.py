"""
Command Execution Server

This module provides a Flask-based REST API for managing and executing commands.
It serves as the backend for the Command Launcher Chrome extension, allowing
users to store, retrieve, and execute shell commands through a web interface.

Key Features:
- Command storage and retrieval
- Command execution with output capture
- CORS support for browser integration
- JSON-based command persistence

The server runs on port 5001 and provides the following endpoints:
- GET /api/commands: Retrieve all stored commands
- POST /api/commands: Add a new command
- POST /api/commands/run: Execute a stored command by index

Dependencies:
    - Flask: Web framework
    - Flask-CORS: Cross-Origin Resource Sharing support
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import subprocess
import os

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# File to store commands persistently
COMMANDS_FILE = "commands.json"

def load_commands():
    """
    Load commands from the persistent storage file.
    
    This function:
    1. Checks if the commands file exists
    2. Creates an empty list if the file doesn't exist
    3. Loads and returns the commands from the file
    
    Returns:
        list: List of command dictionaries, each containing:
            - description: Command description
            - command: The actual shell command
    """
    if not os.path.exists(COMMANDS_FILE):
        return []
    with open(COMMANDS_FILE, "r") as f:
        return json.load(f)

@app.route('/api/commands', methods=['GET'])
def get_commands():
    """
    Retrieve all stored commands.
    
    Returns:
        JSON response containing the list of commands
    """
    return jsonify(load_commands())

@app.route('/api/commands', methods=['POST'])
def add_command():
    """
    Add a new command to the storage.
    
    Expected JSON payload:
        {
            "description": "Command description",
            "command": "shell command to execute"
        }
    
    Returns:
        JSON response with status:
            - success: Command was added successfully
            - error: Failed to add command
    """
    data = request.json
    commands = load_commands()
    commands.append({
        "description": data['description'],
        "command": data['command']
    })
    with open(COMMANDS_FILE, "w") as f:
        json.dump(commands, f, indent=2)
    return jsonify({"status": "success"})

@app.route('/api/commands/run', methods=['POST'])
def run_command():
    """
    Execute a stored command by its index.
    
    Expected JSON payload:
        {
            "index": integer  # Index of the command to execute
        }
    
    Returns:
        JSON response containing:
            - status: "success" or "error"
            - output: Command's stdout output (if successful)
            - error: Error message or stderr output (if failed)
    """
    data = request.json
    command_index = data.get('index')
    commands = load_commands()
    
    if 0 <= command_index < len(commands):
        try:
            result = subprocess.run(
                commands[command_index]['command'],
                shell=True,
                capture_output=True,
                text=True
            )
            return jsonify({
                "status": "success",
                "output": result.stdout,
                "error": result.stderr
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e)
            })
    return jsonify({"status": "error", "error": "Invalid command index"})

if __name__ == '__main__':
    # Start the Flask development server
    app.run(port=5001) 
