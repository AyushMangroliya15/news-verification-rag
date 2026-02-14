'use strict';

// Create context menu item when extension is installed/updated
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'verify-claim',
    title: 'Verify claim',
    contexts: ['selection']
  });
});

// When user clicks "Verify claim" in context menu, get selection and open popup with claim
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'verify-claim' || !info.selectionText) return;
  const claim = info.selectionText.trim();
  if (!claim) return;
  // Store claim for popup to read; then open popup (user may need to click extension icon)
  chrome.storage.local.set({ pendingClaim: claim }, () => {
    chrome.action.openPopup?.().catch(() => {});
    // Fallback: open popup by focusing the extension (user clicks icon to see claim)
    chrome.windows.getCurrent((win) => {
      chrome.action.setBadgeText({ text: '1', tabId: tab.id });
      chrome.action.setBadgeBackgroundColor({ color: '#2563eb', tabId: tab.id });
    });
  });
});

// Clear badge when popup reads the claim
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'POPUP_READY') {
    chrome.storage.local.remove('pendingClaim');
    if (sender.tab?.id) chrome.action.setBadgeText({ text: '', tabId: sender.tab.id });
    sendResponse({ ok: true });
  }
  return true;
});
