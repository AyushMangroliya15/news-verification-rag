// Background script to handle verification API calls

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Background] Message received:', message);
  
  if (message.type === 'VERIFY_CLAIM') {
    const text = message.text;
    console.log('[Background] Verifying claim, text length:', text ? text.length : 0);
    
    if (!text || text.trim().length === 0) {
      console.error('[Background] No text provided for verification');
      sendResponse({ success: false, error: 'No text provided' });
      return false;
    }
    
    // Store verification state as loading
    chrome.storage.local.set({ 
      verificationState: 'loading',
      verificationText: text 
    }, () => {
      if (chrome.runtime.lastError) {
        console.error('[Background] Error storing loading state:', chrome.runtime.lastError.message);
      } else {
        console.log('[Background] Loading state stored successfully');
      }
    });
    
    // Open popup window
    console.log('[Background] Opening popup window...');
    chrome.windows.create({
      url: chrome.runtime.getURL('popup.html'),
      type: 'popup',
      width: 450,
      height: 500
    }, (window) => {
      if (chrome.runtime.lastError) {
        console.error('[Background] Error opening popup:', chrome.runtime.lastError.message);
      } else {
        console.log('[Background] Popup window opened successfully, window ID:', window ? window.id : 'unknown');
      }
    });
    
    // Mock API call - replace with actual API endpoint
    console.log('[Background] Starting verification API call...');
    verifyClaim(text)
      .then((result) => {
        console.log('[Background] Verification completed:', result);
        // Store result
        chrome.storage.local.set({ 
          verificationState: 'completed',
          verificationResult: { success: true, data: result }
        }, () => {
          if (chrome.runtime.lastError) {
            console.error('[Background] Error storing result:', chrome.runtime.lastError.message);
          } else {
            console.log('[Background] Result stored successfully');
          }
        });
        sendResponse({ success: true, data: result });
      })
      .catch((error) => {
        console.error('[Background] Verification error:', error);
        // Store error
        chrome.storage.local.set({ 
          verificationState: 'error',
          verificationResult: { success: false, error: error.message }
        }, () => {
          if (chrome.runtime.lastError) {
            console.error('[Background] Error storing error state:', chrome.runtime.lastError.message);
          } else {
            console.log('[Background] Error state stored successfully');
          }
        });
        sendResponse({ success: false, error: error.message });
      });
    
    // Return true to indicate we will send a response asynchronously
    return true;
  } else {
    console.log('[Background] Unknown message type:', message.type);
  }
});

// Function to verify claim (mock implementation)
async function verifyClaim(text) {
  // Mock API call with timeout
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        verified: true,
        confidence: 0.95,
        sources: [
          "Source 1: Verified information",
          "Source 2: Fact-checked data"
        ],
        summary: `The claim "${text.substring(0, 50)}..." has been verified with high confidence.`
      });
    }, 1000);
  });
  
  // Uncomment and replace with actual API call:
  /*
  try {
    const response = await fetch('YOUR_API_ENDPOINT', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: text })
    });
    return await response.json();
  } catch (error) {
    throw new Error('Failed to verify claim: ' + error.message);
  }
  */
}

