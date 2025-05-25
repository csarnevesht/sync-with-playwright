from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import subprocess
import os

app = Flask(__name__)
CORS(app)

COMMANDS_FILE = "commands.json"

def load_commands():
    if not os.path.exists(COMMANDS_FILE):
        return []
    with open(COMMANDS_FILE, "r") as f:
        return json.load(f)

@app.route('/api/commands', methods=['GET'])
def get_commands():
    return jsonify(load_commands())

@app.route('/api/commands', methods=['POST'])
def add_command():
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
    app.run(port=5001) 
