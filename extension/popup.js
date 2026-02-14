'use strict';

const API_BASE = 'http://localhost:8000';

const claimEl = document.getElementById('claim');
const verifyBtn = document.getElementById('verify');
const statusEl = document.getElementById('status');
const statusTextEl = statusEl ? statusEl.querySelector('.status-text') : null;
const resultEl = document.getElementById('result');
const verdictEl = document.getElementById('verdict');
const verdictTextEl = verdictEl ? verdictEl.querySelector('.verdict-text') : null;
const reasoningEl = document.getElementById('reasoning');
const citationsEl = document.getElementById('citations');

/**
 * Creates a ripple effect on button click.
 * @param {MouseEvent} event - The click event
 */
function createRipple(event) {
  const button = event.currentTarget;
  const ripple = button.querySelector('.button-ripple');
  if (!ripple) return;
  
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = event.clientX - rect.left - size / 2;
  const y = event.clientY - rect.top - size / 2;
  
  ripple.style.width = ripple.style.height = size + 'px';
  ripple.style.left = x + 'px';
  ripple.style.top = y + 'px';
  ripple.style.animation = 'ripple 0.6s ease-out';
  
  setTimeout(() => {
    ripple.style.animation = '';
  }, 600);
}

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
    statusEl.className = 'status ' + (type || '');
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
 * Shows the verification result with animations.
 * @param {string} verdict - The verdict (Supported, Refuted, Not Enough Evidence)
 * @param {string} reasoning - The reasoning text
 * @param {Array} citations - Array of citation objects with title, url, snippet
 */
function showResult(verdict, reasoning, citations) {
  if (!resultEl) return;
  
  resultEl.classList.remove('hidden');
  
  // Update verdict with proper formatting
  const verdictClass = verdict.toLowerCase().replace(/\s+/g, '-');
  if (verdictEl) {
    verdictEl.className = 'verdict ' + verdictClass;
    if (verdictTextEl) {
      verdictTextEl.textContent = verdict;
    } else {
      verdictEl.textContent = verdict;
    }
  }
  
  // Update reasoning with fade-in
  if (reasoningEl) {
    reasoningEl.textContent = reasoning || 'No reasoning provided.';
  }

  // Clear and rebuild citations with staggered animations
  if (citationsEl) {
    citationsEl.innerHTML = '';
    
    if (citations && citations.length > 0) {
      citations.forEach((c, index) => {
        const li = document.createElement('li');
        li.style.animationDelay = `${index * 0.1}s`;
        
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
          const snippetText = c.snippet.length > 120 
            ? c.snippet.slice(0, 120) + '…' 
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
  
  // Scroll result into view smoothly
  setTimeout(() => {
    resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

/**
 * Handles the verification button click and API call.
 */
async function verify() {
  const claim = (claimEl.value || '').trim();
  if (!claim) {
    showStatus('Enter or paste a claim to verify.', 'error');
    // Add shake animation to input
    if (claimEl) {
      claimEl.style.animation = 'shake 0.5s ease';
      setTimeout(() => {
        claimEl.style.animation = '';
      }, 500);
    }
    return;
  }

  // Update button state with animations
  if (verifyBtn) {
    verifyBtn.disabled = true;
    const buttonText = verifyBtn.querySelector('.button-text');
    const buttonLoader = verifyBtn.querySelector('.button-loader');
    if (buttonText) buttonText.classList.add('hidden');
    if (buttonLoader) buttonLoader.classList.remove('hidden');
  }
  
  // Hide previous result with fade out
  if (resultEl) {
    resultEl.style.opacity = '0';
    resultEl.style.transform = 'translateY(-20px)';
    setTimeout(() => {
      resultEl.classList.add('hidden');
      resultEl.style.opacity = '';
      resultEl.style.transform = '';
    }, 300);
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
      return;
    }
    
    // Small delay before showing result for smoother transition
    setTimeout(() => {
      showResult(
        data.verdict || 'Not Enough Evidence',
        data.reasoning || '',
        data.citations || []
      );
    }, 200);
    
  } catch (e) {
    hideStatus();
    showStatus('Network error. Is the backend running at ' + API_BASE + '?', 'error');
  } finally {
    // Reset button state
    if (verifyBtn) {
      verifyBtn.disabled = false;
      const buttonText = verifyBtn.querySelector('.button-text');
      const buttonLoader = verifyBtn.querySelector('.button-loader');
      if (buttonText) buttonText.classList.remove('hidden');
      if (buttonLoader) buttonLoader.classList.add('hidden');
    }
  }
}

// Event listeners
if (verifyBtn) {
  verifyBtn.addEventListener('click', (e) => {
    createRipple(e);
    verify();
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
  
  // Add focus animation
  claimEl.addEventListener('focus', () => {
    claimEl.style.transform = 'translateY(-2px)';
  });
  
  claimEl.addEventListener('blur', () => {
    claimEl.style.transform = '';
  });
}

// Add logo interaction
const logo3d = document.querySelector('.logo-3d');
if (logo3d) {
  logo3d.addEventListener('mouseenter', () => {
    logo3d.style.animationPlayState = 'paused';
  });
  
  logo3d.addEventListener('mouseleave', () => {
    logo3d.style.animationPlayState = 'running';
  });
  
  // Click to reset animation
  logo3d.addEventListener('click', () => {
    logo3d.style.animation = 'none';
    setTimeout(() => {
      logo3d.style.animation = 'logoRotate 8s linear infinite, logoFloat 3s ease-in-out infinite';
    }, 10);
  });
}

// Pre-fill claim from context menu (stored by background)
chrome.storage.local.get(['pendingClaim'], (o) => {
  if (o.pendingClaim && claimEl) {
    claimEl.value = o.pendingClaim;
    chrome.storage.local.remove('pendingClaim');
    chrome.runtime.sendMessage({ type: 'POPUP_READY' }).catch(() => {});
    
    // Focus the textarea and scroll to bottom with animation
    setTimeout(() => {
      claimEl.focus();
      claimEl.scrollTop = claimEl.scrollHeight;
      // Add a subtle highlight animation
      claimEl.style.boxShadow = '0 0 0 4px rgba(230, 80, 27, 0.3)';
      setTimeout(() => {
        claimEl.style.boxShadow = '';
      }, 1000);
    }, 100);
  }
});

// Add page load animation
window.addEventListener('load', () => {
  document.body.style.opacity = '0';
  setTimeout(() => {
    document.body.style.transition = 'opacity 0.5s ease';
    document.body.style.opacity = '1';
  }, 50);
});
