'use strict';

const API_BASE = 'http://localhost:8000';

const claimEl = document.getElementById('claim');
const verifyBtn = document.getElementById('verify');
const statusEl = document.getElementById('status');
const statusTextEl = statusEl ? statusEl.querySelector('.status-text') : null;
const inputPhaseEl = document.getElementById('inputPhase');
const resultsPhaseEl = document.getElementById('resultsPhase');
const verdictEl = document.getElementById('verdict');
const verdictTextEl = verdictEl ? verdictEl.querySelector('.verdict-text') : null;
const reasoningEl = document.getElementById('reasoning');
const citationsEl = document.getElementById('citations');
const headerClaimEl = document.getElementById('headerClaim');
const newClaimBtn = document.getElementById('newClaim');

/**
 * Shows a status message with animation.
 * @param {string} msg - The message to display
 * @param {string} type - The type of status ('loading' or 'error')
 */
function showStatus(msg, type) {
  if (statusTextEl) {
    statusTextEl.textContent = msg;
  } else if (statusEl) {
    statusEl.textContent = msg;
  }
  if (statusEl) {
    statusEl.className = 'status-message ' + (type || '');
    statusEl.classList.remove('hidden');
  }
}

/**
 * Hides the status message.
 */
function hideStatus() {
  if (statusEl) {
    statusEl.classList.add('hidden');
  }
}

/**
 * Saves the current verification state to Chrome storage.
 * @param {string} claimText - The claim text
 * @param {string} verdict - The verdict
 * @param {string} reasoning - The reasoning
 * @param {Array} citations - Array of citation objects
 */
function saveState(claimText, verdict, reasoning, citations) {
  chrome.storage.local.set({
    savedState: {
      claim: claimText,
      verdict: verdict,
      reasoning: reasoning,
      citations: citations,
      timestamp: Date.now()
    }
  });
}

/**
 * Clears the saved state from Chrome storage.
 */
function clearSavedState() {
  chrome.storage.local.remove(['savedState']);
}

/**
 * Restores the verification state from Chrome storage.
 * @param {Object} state - The saved state object
 */
function restoreState(state) {
  if (state && state.claim) {
    showResult(state.verdict, state.reasoning, state.citations, state.claim);
  }
}

/**
 * Shows the verification result with animations.
 * @param {string} verdict - The verdict (Supported, Refuted, Not Enough Evidence)
 * @param {string} reasoning - The reasoning text
 * @param {Array} citations - Array of citation objects with title, url, snippet
 * @param {string} claimText - The original claim text to display in header
 */
function showResult(verdict, reasoning, citations, claimText) {
  // Hide input phase and show results phase
  if (inputPhaseEl) {
    inputPhaseEl.classList.add('hidden');
  }
  if (resultsPhaseEl) {
    resultsPhaseEl.classList.remove('hidden');
  }
  
  // Show claim in header
  if (headerClaimEl && claimText) {
    headerClaimEl.textContent = claimText;
    headerClaimEl.classList.remove('hidden');
  }
  
  // Show new claim button
  if (newClaimBtn) {
    newClaimBtn.classList.remove('hidden');
  }
  
  // Map API verdict to CSS class (supported, refuted, not-enough, mixed-disputed, unverifiable)
  const verdictClassMap = {
    'supported': 'supported',
    'refuted': 'refuted',
    'not enough evidence': 'not-enough',
    'mixed / disputed': 'mixed-disputed',
    'unverifiable': 'unverifiable'
  };
  const verdictClass = verdictClassMap[verdict.toLowerCase()] || 'not-enough';
  if (verdictEl) {
    verdictEl.className = 'verdict-badge ' + verdictClass;
    if (verdictTextEl) {
      verdictTextEl.textContent = verdict;
    }
  }

  // Update reasoning
  if (reasoningEl) {
    reasoningEl.textContent = reasoning || 'No reasoning provided.';
  }

  // Clear and rebuild citations
  if (citationsEl) {
    citationsEl.innerHTML = '';
    
    if (citations && citations.length > 0) {
      citations.forEach((c) => {
        const li = document.createElement('li');
        
        const titleLink = document.createElement('a');
        titleLink.href = c.url || '#';
        titleLink.target = '_blank';
        titleLink.rel = 'noopener';
        titleLink.className = 'citation-title';
        titleLink.textContent = c.title || 'Source';
        li.appendChild(titleLink);
        
        if (c.snippet) {
          const snippetSpan = document.createElement('span');
          snippetSpan.className = 'citation-snippet';
          const snippetText = c.snippet.length > 150 
            ? c.snippet.slice(0, 150) + '…' 
            : c.snippet;
          snippetSpan.textContent = snippetText;
          li.appendChild(snippetSpan);
        }
        
        citationsEl.appendChild(li);
      });
    } else {
      const li = document.createElement('li');
      li.className = 'no-citations';
      li.textContent = 'No citations available.';
      citationsEl.appendChild(li);
    }
  }
  
  // Save state to Chrome storage
  if (claimText) {
    saveState(claimText, verdict, reasoning, citations);
  }
}

/**
 * Resets the UI to initial state for a new claim.
 */
function resetToInitialView() {
  // Clear saved state
  clearSavedState();
  
  // Show input phase, hide results phase
  if (inputPhaseEl) {
    inputPhaseEl.classList.remove('hidden');
  }
  if (resultsPhaseEl) {
    resultsPhaseEl.classList.add('hidden');
  }
  
  // Hide claim in header
  if (headerClaimEl) {
    headerClaimEl.classList.add('hidden');
    headerClaimEl.textContent = '';
  }
  
  // Hide new claim button
  if (newClaimBtn) {
    newClaimBtn.classList.add('hidden');
  }
  
  // Reset verify button state
  if (verifyBtn) {
    verifyBtn.disabled = false;
    const buttonLabel = verifyBtn.querySelector('.button-label');
    const buttonLoader = verifyBtn.querySelector('.button-loader');
    if (buttonLabel) buttonLabel.classList.remove('hidden');
    if (buttonLoader) buttonLoader.classList.add('hidden');
  }
  
  // Clear input
  if (claimEl) {
    claimEl.value = '';
    claimEl.focus();
  }
  
  // Hide status
  hideStatus();
}

/**
 * Handles the verification button click and API call.
 */
async function verify() {
  const claim = (claimEl.value || '').trim();
  if (!claim) {
    showStatus('Enter or paste a claim to verify.', 'error');
    return;
  }

  // Store claim text for display in header
  const claimText = claim;

  // Update button state
  if (verifyBtn) {
    verifyBtn.disabled = true;
    const buttonLabel = verifyBtn.querySelector('.button-label');
    const buttonLoader = verifyBtn.querySelector('.button-loader');
    if (buttonLabel) buttonLabel.classList.add('hidden');
    if (buttonLoader) buttonLoader.classList.remove('hidden');
  }
  
  // Hide previous results
  if (resultsPhaseEl) {
    resultsPhaseEl.classList.add('hidden');
  }
  
  showStatus('Verifying claim…', 'loading');

  try {
    const res = await fetch(API_BASE + '/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim }),
    });
    
    const data = await res.json().catch(() => ({}));
    hideStatus();
    
    if (!res.ok) {
      showStatus('Request failed: ' + (data.detail || res.statusText), 'error');
      // Reset button state on error
      if (verifyBtn) {
        verifyBtn.disabled = false;
        const buttonLabel = verifyBtn.querySelector('.button-label');
        const buttonLoader = verifyBtn.querySelector('.button-loader');
        if (buttonLabel) buttonLabel.classList.remove('hidden');
        if (buttonLoader) buttonLoader.classList.add('hidden');
      }
      return;
    }
    
    // Small delay before showing result for smoother transition
    setTimeout(() => {
      showResult(
        data.verdict || 'Not Enough Evidence',
        data.reasoning || '',
        data.citations || [],
        claimText
      );
    }, 200);
    
  } catch (e) {
    hideStatus();
    showStatus('Network error. Is the backend running at ' + API_BASE + '?', 'error');
    // Reset button state on error
    if (verifyBtn) {
      verifyBtn.disabled = false;
      const buttonLabel = verifyBtn.querySelector('.button-label');
      const buttonLoader = verifyBtn.querySelector('.button-loader');
      if (buttonLabel) buttonLabel.classList.remove('hidden');
      if (buttonLoader) buttonLoader.classList.add('hidden');
    }
  }
}

// Event listeners
if (verifyBtn) {
  verifyBtn.addEventListener('click', () => {
    verify();
  });
}

// New claim button event listener
if (newClaimBtn) {
  newClaimBtn.addEventListener('click', () => {
    resetToInitialView();
  });
}

// Allow Enter key to trigger verification (Ctrl+Enter or Cmd+Enter)
if (claimEl) {
  claimEl.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      verify();
    }
  });
}

// Initialize popup: check for pending claim or restore saved state
chrome.storage.local.get(['pendingClaim', 'savedState'], (o) => {
  // Priority 1: If there's a pending claim from context menu, use it
  if (o.pendingClaim && claimEl) {
    claimEl.value = o.pendingClaim;
    chrome.storage.local.remove('pendingClaim');
    chrome.runtime.sendMessage({ type: 'POPUP_READY' }).catch(() => {});
    
    // Focus the textarea
    setTimeout(() => {
      claimEl.focus();
      claimEl.scrollTop = claimEl.scrollHeight;
    }, 100);
  } 
  // Priority 2: If there's saved state, restore it
  else if (o.savedState && o.savedState.claim) {
    const state = o.savedState;
    // Only restore if state is less than 1 hour old
    const oneHour = 60 * 60 * 1000;
    if (Date.now() - state.timestamp < oneHour) {
      restoreState(state);
    } else {
      // State is too old, clear it
      clearSavedState();
    }
  }
});
