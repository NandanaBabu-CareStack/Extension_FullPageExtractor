document.getElementById('extractRedirect').addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            files: ['content.js']
        });
    });
});

document.getElementById('viewData').addEventListener('click', () => {
    chrome.storage.local.get(['cleanedText', 'lastExtractedUrl'], (data) => {
        const output = document.getElementById('output');
        if (data.cleanedText) {
            output.textContent = `URL: ${data.lastExtractedUrl || 'Unknown'}\n\n${data.cleanedText}`;
        } else {
            output.textContent = 'No data extracted yet. Use Extract & Redirect first.';
        }
    });
});

// Load last extracted data on popup open

chrome.storage.local.get(['cleanedText'], (data) => {
    if (data.cleanedText) {
        document.getElementById('output').textContent = data.cleanedText;
    }
});