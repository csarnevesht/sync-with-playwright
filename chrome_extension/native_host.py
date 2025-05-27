#!/usr/bin/env python3
import sys
import json
import struct
import subprocess
import os
import signal
import time

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(os.path.dirname(SCRIPT_DIR), 'server.py')

server_process = None

def send_message(message):
    """Send a message to Chrome."""
    sys.stdout.buffer.write(struct.pack('I', len(message)))
    sys.stdout.buffer.write(message.encode('utf-8'))
    sys.stdout.buffer.flush()

def read_message():
    """Read a message from Chrome."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def is_server_running():
    try:
        import requests
        requests.get('http://localhost:5001/api/commands', timeout=1)
        return True
    except:
        return False

def start_server():
    global server_process
    if is_server_running():
        return True
    try:
        server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for server to start
        for _ in range(10):
            if is_server_running():
                return True
            time.sleep(0.5)
        return False
    except Exception as e:
        return False

def stop_server():
    global server_process
    # Try to stop by process if we started it
    if server_process and server_process.poll() is None:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None
        return True
    # Try to stop by finding the process (if started elsewhere)
    # (Optional: implement with psutil if needed)
    return False

def restart_server():
    stop_server()
    return start_server()

def main():
    while True:
        message = read_message()
        if message is None:
            break
        action = message.get('action')
        if action == 'start_server':
            success = start_server()
            send_message(json.dumps({
                'status': 'success' if success else 'error',
                'message': 'Server started' if success else 'Failed to start server'
            }))
        elif action == 'stop_server':
            success = stop_server()
            send_message(json.dumps({
                'status': 'success' if success else 'error',
                'message': 'Server stopped' if success else 'Failed to stop server'
            }))
        elif action == 'restart_server':
            success = restart_server()
            send_message(json.dumps({
                'status': 'success' if success else 'error',
                'message': 'Server restarted' if success else 'Failed to restart server'
            }))

if __name__ == '__main__':
    main() 