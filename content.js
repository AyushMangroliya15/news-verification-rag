// Content script to show "Verify claim" button when text is selected

let verifyButton = null;

// Function to create and show the "Verify claim" button
function showVerifyButton() {
  // Remove existing button if any
  if (verifyButton) {
    verifyButton.remove();
  }

  const selection = window.getSelection();
  if (!selection || selection.toString().trim().length === 0) {
    return;
  }

  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  
  // Capture selected text NOW before it gets lost when button is clicked
  const selectedText = selection.toString().trim();
  console.log('[Content Script] Captured selected text when creating button, length:', selectedText.length);

  // Create the button
  verifyButton = document.createElement('div');
  verifyButton.id = 'verify-claim-button';
  verifyButton.textContent = 'Verify claim';
  // Store the selected text as a data attribute so it's available when clicked
  verifyButton.dataset.selectedText = selectedText;
  verifyButton.style.cssText = `
    position: fixed;
    top: ${rect.top + window.scrollY - 40}px;
    left: ${rect.left + window.scrollX}px;
    background: #4CAF50;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
    z-index: 10000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    font-family: Arial, sans-serif;
  `;

  verifyButton.addEventListener('click', async (e) => {
    console.log('[Content Script] Verify claim button clicked', e);
    e.stopPropagation();
    e.preventDefault();
    
    // Get the selected text from the button's data attribute (captured when button was created)
    const selectedText = verifyButton.dataset.selectedText || '';
    console.log('[Content Script] Verify claim button clicked, selected text from dataset:', selectedText);
    
    if (selectedText && selectedText.trim().length > 0) {
      // Hide the button
      verifyButton.style.display = 'none';
      
      console.log('[Content Script] Sending message to background script with text length:', selectedText.length);
      
      // Store selected text and trigger verification (this will open popup)
      chrome.runtime.sendMessage(
        { type: 'VERIFY_CLAIM', text: selectedText.trim() },
        (response) => {
          if (chrome.runtime.lastError) {
            console.error('[Content Script] Error sending message:', chrome.runtime.lastError.message);
            return;
          }
          console.log('[Content Script] Message sent successfully, response:', response);
        }
      );
    } else {
      console.warn('[Content Script] No text selected when button was clicked. Dataset value:', verifyButton.dataset.selectedText);
    }
  });

  document.body.appendChild(verifyButton);
}


// Listen for text selection
document.addEventListener('mouseup', () => {
  const selection = window.getSelection();
  const selectedText = selection ? selection.toString().trim() : '';
  console.log('[Content Script] Mouse up event, selected text length:', selectedText.length);
  
  if (selectedText.length > 0) {
    console.log('[Content Script] Showing verify button');
    showVerifyButton();
  } else {
    // Hide button if no selection
    if (verifyButton) {
      verifyButton.style.display = 'none';
    }
  }
});

// Hide button when clicking elsewhere (but not on the button itself)
document.addEventListener('mousedown', (e) => {
  if (verifyButton && e.target !== verifyButton && !verifyButton.contains(e.target)) {
    verifyButton.style.display = 'none';
  }
});

