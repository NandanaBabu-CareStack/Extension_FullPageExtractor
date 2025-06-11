// Handle extension click

chrome.action.onClicked.addListener((tab) => {
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"]
  });
});

// Handle messages from content script

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "openNewTab") {
    chrome.tabs.create({
      url: request.url,
      active: true
    });
  }
});