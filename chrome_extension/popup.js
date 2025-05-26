const SERVER_URL = 'http://localhost:5001';
let nativePort = null;

function debugLog(msg) {
  const debug = document.getElementById('debug');
  if (debug) debug.textContent += msg + '\n';
}

function clearDebug() {
    const debug = document.getElementById('debug');
    if (debug) debug.textContent = '';
}

async function connectNativeHost() {
  try {
    nativePort = chrome.runtime.connectNative('com.command_launcher');
    nativePort.onMessage.addListener((response) => {
      debugLog('Native host message: ' + JSON.stringify(response));
      if (response.status === 'success') {
        loadCommands();
      } else {
        showOutput('Error: ' + response.message);
      }
    });
    nativePort.onDisconnect.addListener(() => {
      debugLog('Native host disconnected');
      showOutput('Native host disconnected. Please check if the native host is properly installed.');
    });
    debugLog('Connected to native host');
    return true;
  } catch (error) {
    debugLog('Error connecting to native host: ' + error);
    console.error('Error connecting to native host:', error);
    return false;
  }
}

async function startServer() {
  if (!nativePort) {
    const connected = await connectNativeHost();
    if (!connected) {
      showOutput('Error: Could not connect to native host. Please check if the native host is properly installed.');
      return false;
    }
  }
  debugLog('Requesting server start');
  nativePort.postMessage({ action: 'start_server' });
  return true;
}

async function loadCommands() {
  debugLog('Loading commands...');
  try {
    const response = await fetch(`${SERVER_URL}/api/commands`);
    const commands = await response.json();
    debugLog('Commands loaded: ' + JSON.stringify(commands));
    displayCommands(commands);
  } catch (error) {
    debugLog('Error loading commands: ' + error);
    console.error('Error loading commands:', error);
    // Try to start the server if it's not running
    const serverStarted = await startServer();
    if (!serverStarted) {
      showOutput('Error loading commands. Make sure the server is running.');
    }
  }
}

function displayCommands(commands) {
  debugLog('Displaying commands: ' + JSON.stringify(commands));
  const commandList = document.getElementById('commandList');
  commandList.innerHTML = '';
  if (!commands.length) {
    commandList.textContent = 'No commands found.';
    debugLog('No commands found.');
    return;
  }
  commands.forEach((command, index) => {
    const commandItem = document.createElement('div');
    commandItem.className = 'command-item';
    const description = document.createElement('div');
    description.className = 'command-description';
    description.textContent = command.description;
    const runButton = document.createElement('button');
    runButton.className = 'run-button';
    runButton.textContent = 'Run';
    runButton.onclick = () => runCommand(index);
    commandItem.appendChild(description);
    commandItem.appendChild(runButton);
    commandList.appendChild(commandItem);
  });
}

async function runCommand(index) {
  debugLog('Running command at index: ' + index);
  showOutput(''); // Clear output immediately when Run is clicked
  clearDebug();   // Optionally clear debug log as well
  try {
    const response = await fetch(`${SERVER_URL}/api/commands/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ index }),
    });
    const result = await response.json();
    debugLog('Command result: ' + JSON.stringify(result));
    if (result.status === 'success') {
      showOutput(result.output || 'Command executed successfully.');
    } else {
      showOutput(`Error: ${result.error}`);
    }
  } catch (error) {
    debugLog('Error running command: ' + error);
    console.error('Error running command:', error);
    showOutput('Error running command. Make sure the server is running.');
  }
}

function showOutput(message) {
    const output = document.getElementById('output');
    output.textContent = message;
    output.style.display = message ? 'block' : 'none';
    debugLog('Output: ' + message);
}

// Load commands when the popup opens
document.addEventListener('DOMContentLoaded', loadCommands); 