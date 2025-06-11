function getVisibleTextFromPage() {
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    return (
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );
  };

  const getTextFromNode = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent.trim();
    }

    if (node.nodeType === Node.ELEMENT_NODE && isVisible(node)) {
      const tag = node.tagName.toLowerCase();
      let text = "";

      if (["h1", "h2", "h3", "h4", "strong", "b"].includes(tag)) {
        text += "\n\n🔹 " + node.innerText.trim() + " 🔹\n";
      } else if (["li", "p", "span", "td", "th"].includes(tag)) {
        text += node.innerText.trim() + "\n";
      } else if (tag === "table") {
        const rows = node.querySelectorAll("tr");
        rows.forEach((row) => {
          const cells = row.querySelectorAll("td, th");
          const rowText = Array.from(cells)
            .map((c) => c.innerText.trim())
            .join(" | ");
          text += rowText + "\n";
        });
      } else {
        node.childNodes.forEach((child) => {
          text += getTextFromNode(child);
        });
      }

      return text;
    }

    return "";
  };

  const pageContent = getTextFromNode(document.body);
  chrome.storage.local.set({
    cleanedText: pageContent,
    lastExtractedUrl: window.location.href,
    lastExtractedTime: new Date().toISOString()
  });
}

function handleNavigation() {
  const currentUrl = window.location.href;

  if (currentUrl.includes('eligibility.carestackqa.com')) {

    // Store that we're extracting from eligibility site

    chrome.storage.local.set({
      siteContext: 'eligibility',
      originalUrl: currentUrl
    });

    // Open Cigna in new tab

    chrome.runtime.sendMessage({
      action: "openNewTab",
      url: "https://cignaforhcp.cigna.com/app/login?unifyAutofillApp=eyJhcHBJZCI6IjAxMDgzYjY0LTRiYmQtNDQzMC05ODBmLWQxOTc1M2U2YzU1NCJ9"
    });
  }
  else if (currentUrl.includes('cignaforhcp.cigna.com')) {

    // Store that we're extracting from Cigna site

    chrome.storage.local.set({
      siteContext: 'cigna'
    });
  }
}

// Main execution

getVisibleTextFromPage();
handleNavigation();