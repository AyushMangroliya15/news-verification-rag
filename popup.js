// Popup script to show loading state and verification results

let contentDiv = null;

// Function to get content div (with safety check)
function getContentDiv() {
  if (!contentDiv) {
    contentDiv = document.getElementById('content');
    if (!contentDiv) {
      console.error('[Popup] Content div not found!');
      return null;
    }
  }
  return contentDiv;
}

// Function to show loading state
function showLoading() {
  const div = getContentDiv();
  if (!div) return;
  div.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <div>Verifying claim...</div>
    </div>
  `;
}

// Function to show result
function showResult(result) {
  if (result && result.success && result.data) {
    const data = result.data;
    let html = '<div class="result">';
    
    if (data.verified !== undefined) {
      const statusClass = data.verified ? 'verified' : 'not-verified';
      const statusIcon = data.verified ? '✅' : '❌';
      const statusText = data.verified ? 'Verified' : 'Not Verified';
      html += `<div class="status ${statusClass}">${statusIcon} ${statusText}</div>`;
    }
    
    if (data.confidence !== undefined) {
      html += `<div class="info-item"><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(1)}%</div>`;
    }
    
    if (data.summary) {
      html += `<div class="summary">${data.summary}</div>`;
    }
    
    if (data.sources && Array.isArray(data.sources) && data.sources.length > 0) {
      html += '<div class="sources"><strong>Sources:</strong><ul>';
      data.sources.forEach(source => {
        html += `<li>${source}</li>`;
      });
      html += '</ul></div>';
    }
    
    if (!data.verified && !data.confidence && !data.summary && !data.sources) {
      html += `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    }
    
    html += '</div>';
    const div = getContentDiv();
    if (!div) return;
    div.innerHTML = html;
  } else if (result && result.error) {
    const div = getContentDiv();
    if (!div) return;
    div.innerHTML = `<div class="error">❌ Error: ${result.error}</div>`;
  } else {
    const div = getContentDiv();
    if (!div) return;
    div.innerHTML = `<div class="error">❌ Unexpected error occurred</div>`;
  }
}

// Function to show empty state
function showEmptyState() {
  const div = getContentDiv();
  if (!div) return;
  div.innerHTML = `
    <div class="empty-state">
      Select text on a webpage and click "Verify claim" to get started.
    </div>
  `;
}

let pollInterval = null;

// Check verification state when popup opens
async function checkVerificationState() {
  console.log('[Popup] Checking verification state...');
  try {
    const data = await chrome.storage.local.get(['verificationState', 'verificationText', 'verificationResult']);
    console.log('[Popup] Storage data:', data);
    
    if (data.verificationState === 'loading') {
      console.log('[Popup] State is loading, showing loading spinner');
      showLoading();
      // Poll for result
      pollInterval = setInterval(async () => {
        try {
          const updated = await chrome.storage.local.get(['verificationState', 'verificationResult']);
          if (updated.verificationState === 'completed' || updated.verificationState === 'error') {
            if (pollInterval) {
              clearInterval(pollInterval);
              pollInterval = null;
            }
            showResult(updated.verificationResult);
            // Clear verification state after showing (with delay to allow user to see result)
            setTimeout(() => {
              chrome.storage.local.remove(['verificationState', 'verificationText', 'verificationResult']);
            }, 5000);
          }
        } catch (error) {
          console.error('Error polling:', error);
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
        }
      }, 200);
      
      // Stop polling after 30 seconds
      setTimeout(() => {
        if (pollInterval) {
          clearInterval(pollInterval);
          pollInterval = null;
          const div = getContentDiv();
          if (div) {
            div.innerHTML = '<div class="error">⏱️ Verification timed out. Please try again.</div>';
          }
        }
      }, 30000);
    } else if (data.verificationState === 'completed' || data.verificationState === 'error') {
      console.log('[Popup] State is', data.verificationState, ', showing result');
      showResult(data.verificationResult);
      // Clear verification state after showing
      setTimeout(() => {
        chrome.storage.local.remove(['verificationState', 'verificationText', 'verificationResult']);
      }, 5000);
    } else {
      console.log('[Popup] No verification state found, showing empty state');
      showEmptyState();
    }
  } catch (error) {
    console.error('Error checking verification state:', error);
    showEmptyState();
  }
}

// Listen for storage changes (in case verification completes while popup is open)
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && changes.verificationState) {
    if (changes.verificationState.newValue === 'completed' || changes.verificationState.newValue === 'error') {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      chrome.storage.local.get(['verificationResult']).then(data => {
        showResult(data.verificationResult);
      });
    }
  }
});

// Initialize when popup opens
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Popup] DOMContentLoaded, initializing...');
  checkVerificationState();
});

// Also check immediately in case DOMContentLoaded already fired
if (document.readyState === 'loading') {
  console.log('[Popup] Document still loading, waiting for DOMContentLoaded');
} else {
  console.log('[Popup] Document already loaded, checking state immediately');
  checkVerificationState();
}
