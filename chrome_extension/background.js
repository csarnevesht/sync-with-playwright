// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// Listen for extension startup
chrome.runtime.onStartup.addListener(() => {
  console.log('Extension started');
});

// Keep the service worker alive
chrome.runtime.onConnect.addListener((port) => {
  port.onDisconnect.addListener(() => {
    console.log('Port disconnected');
  });
}); 