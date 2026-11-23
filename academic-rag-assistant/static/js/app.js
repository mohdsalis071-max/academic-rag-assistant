/**
 * ScholarRAG – AI Academic Assistant
 * Modern Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    studyMode: 'general',
    docFilter: '',
    documents: [],
    messages: [],
    isLoading: false,
    apiKeyConfigured: false,
    theme: localStorage.getItem('scholar_theme') || 'dark'
  };

  // DOM Elements
  const elements = {
    // Layout & Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarOverlay: document.getElementById('sidebar-overlay'),
    sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
    sidebarCloseBtn: document.getElementById('sidebar-close-btn'),
    newChatBtn: document.getElementById('new-chat-btn'),
    clearChatBtn: document.getElementById('clear-chat-btn'),
    themeToggleBtn: document.getElementById('theme-toggle-btn'),
    themeIconSun: document.getElementById('theme-icon-sun'),
    themeIconMoon: document.getElementById('theme-icon-moon'),

    // Study Modes
    modeButtons: document.querySelectorAll('.mode-item'),
    activeModeLabel: document.getElementById('active-mode-label'),

    // Documents
    docCountBadge: document.getElementById('doc-count-badge'),
    dropzone: document.getElementById('dropzone'),
    dropzoneTrigger: document.getElementById('dropzone-trigger'),
    fileInput: document.getElementById('file-input'),
    uploadStatus: document.getElementById('upload-status'),
    uploadStatusText: document.getElementById('upload-status-text'),
    documentList: document.getElementById('document-list'),
    docFilterSelect: document.getElementById('doc-filter-select'),
    activeDocFilter: document.getElementById('active-doc-filter'),
    uploadShortcutBtn: document.getElementById('upload-shortcut-btn'),

    // Chat
    messagesScroll: document.getElementById('messages-scroll'),
    welcomeHero: document.getElementById('welcome-hero'),
    chatMessages: document.getElementById('chat-messages'),
    loadingBubble: document.getElementById('loading-bubble'),
    loadingStatusText: document.getElementById('loading-status-text'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    starterCards: document.querySelectorAll('.starter-card'),

    // API Key & Status
    statusDot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    apiKeyBtn: document.getElementById('api-key-btn'),
    apiModal: document.getElementById('api-modal'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),
    modalSaveBtn: document.getElementById('modal-save-btn'),
    modalApiKeyInput: document.getElementById('modal-api-key-input'),
    modalFeedback: document.getElementById('modal-feedback'),

    // Toasts
    toastContainer: document.getElementById('toast-container')
  };

  // Initialize
  initTheme();
  setupEventListeners();
  checkSystemHealth();
  fetchDocuments();

  // =========================================================================
  // Theme Management
  // =========================================================================
  function initTheme() {
    if (state.theme === 'light') {
      document.body.classList.remove('theme-dark');
      document.body.classList.add('theme-light');
      elements.themeIconSun.classList.remove('hidden');
      elements.themeIconMoon.classList.add('hidden');
    } else {
      document.body.classList.remove('theme-light');
      document.body.classList.add('theme-dark');
      elements.themeIconSun.classList.add('hidden');
      elements.themeIconMoon.classList.remove('hidden');
    }
  }

  function toggleTheme() {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    state.theme = newTheme;
    localStorage.setItem('scholar_theme', newTheme);
    initTheme();
  }

  // =========================================================================
  // Event Listeners
  // =========================================================================
  function setupEventListeners() {
    // Theme toggle
    elements.themeToggleBtn.addEventListener('click', toggleTheme);

    // Sidebar toggles for mobile
    if (elements.sidebarToggleBtn) {
      elements.sidebarToggleBtn.addEventListener('click', () => {
        elements.sidebar.classList.add('open');
        elements.sidebarOverlay.classList.add('active');
      });
    }

    if (elements.sidebarCloseBtn) {
      elements.sidebarCloseBtn.addEventListener('click', closeMobileSidebar);
    }
    if (elements.sidebarOverlay) {
      elements.sidebarOverlay.addEventListener('click', closeMobileSidebar);
    }

    // New / Clear Chat
    elements.newChatBtn.addEventListener('click', resetChat);
    elements.clearChatBtn.addEventListener('click', resetChat);

    // Study Modes
    elements.modeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        elements.modeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.studyMode = btn.dataset.mode;
        const name = btn.querySelector('.mode-name').textContent;
        elements.activeModeLabel.textContent = `Mode: ${name}`;
        showToast(`Switched mode to: ${name}`, 'info');
      });
    });

    // File Upload Trigger
    elements.dropzoneTrigger.addEventListener('click', () => elements.fileInput.click());
    if (elements.uploadShortcutBtn) {
      elements.uploadShortcutBtn.addEventListener('click', () => elements.fileInput.click());
    }
    elements.fileInput.addEventListener('change', handleFileSelect);

    // Drag and Drop Upload
    elements.dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      elements.dropzone.classList.add('dragover');
    });

    elements.dropzone.addEventListener('dragleave', () => {
      elements.dropzone.classList.remove('dragover');
    });

    elements.dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      elements.dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadFiles(e.dataTransfer.files);
      }
    });

    // Document Filter Select
    elements.docFilterSelect.addEventListener('change', (e) => {
      state.docFilter = e.target.value;
      if (state.docFilter) {
        const selectedDoc = state.documents.find(d => d.id === state.docFilter);
        elements.activeDocFilter.textContent = `Focus: ${selectedDoc ? selectedDoc.filename : 'Document'}`;
      } else {
        elements.activeDocFilter.textContent = 'All Uploaded Materials';
      }
    });

    // Starter Prompt Cards
    elements.starterCards.forEach(card => {
      card.addEventListener('click', () => {
        const prompt = card.dataset.prompt;
        if (prompt) {
          elements.chatInput.value = prompt;
          submitChatQuery(prompt);
        }
      });
    });

    // Chat Form Submit & Auto-resize
    elements.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const message = elements.chatInput.value.trim();
      if (!message || state.isLoading) return;
      submitChatQuery(message);
    });

    elements.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        elements.chatForm.dispatchEvent(new Event('submit'));
      }
    });

    elements.chatInput.addEventListener('input', () => {
      elements.chatInput.style.height = 'auto';
      elements.chatInput.style.height = Math.min(elements.chatInput.scrollHeight, 180) + 'px';
    });

    // API Key Modal
    elements.apiKeyBtn.addEventListener('click', openApiKeyModal);
    elements.modalCloseBtn.addEventListener('click', closeApiKeyModal);
    elements.modalCancelBtn.addEventListener('click', closeApiKeyModal);
    elements.modalSaveBtn.addEventListener('click', saveApiKey);
  }

  function closeMobileSidebar() {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('active');
  }

  // =========================================================================
  // API Health & Status
  // =========================================================================
  async function checkSystemHealth() {
    try {
      const res = await fetch('/health');
      if (!res.ok) throw new Error('Health check failed');
      const data = await res.json();

      state.apiKeyConfigured = data.api_key_configured;
      updateStatusUI(data.api_key_configured);
    } catch (err) {
      console.error('System health check error:', err);
      updateStatusUI(false, 'Server offline');
    }
  }

  function updateStatusUI(configured, customText = null) {
    if (configured) {
      elements.statusDot.className = 'status-dot green';
      elements.statusText.textContent = customText || 'Gemini Connected';
    } else {
      elements.statusDot.className = 'status-dot amber';
      elements.statusText.textContent = customText || 'API Key Needed';
    }
  }

  // =========================================================================
  // Document Management (Upload, List, Delete)
  // =========================================================================
  async function fetchDocuments() {
    try {
      const res = await fetch('/documents');
      if (!res.ok) throw new Error('Failed to load documents');
      const data = await res.json();
      state.documents = data.documents || [];
      renderDocumentsList();
      updateFilterDropdown();
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  }

  function renderDocumentsList() {
    const count = state.documents.length;
    elements.docCountBadge.textContent = `${count} ${count === 1 ? 'PDF' : 'PDFs'}`;

    if (count === 0) {
      elements.documentList.innerHTML = `
        <div class="empty-docs-placeholder">
          <span>No PDFs uploaded yet.</span>
          <p>Upload lecture notes to ask curriculum-specific questions.</p>
        </div>
      `;
      return;
    }

    elements.documentList.innerHTML = state.documents.map(doc => `
      <div class="doc-card" data-id="${doc.id}">
        <div class="doc-info">
          <div class="doc-pdf-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div class="doc-details">
            <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
            <div class="doc-meta">
              <span>${doc.total_pages} pages</span>
              <span>•</span>
              <span>${doc.file_size_formatted || doc.file_size}</span>
            </div>
          </div>
        </div>
        <button class="doc-delete-btn" title="Remove from knowledge base" onclick="deleteDocument('${doc.id}', event)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `).join('');
  }

  function updateFilterDropdown() {
    const currentVal = elements.docFilterSelect.value;
    elements.docFilterSelect.innerHTML = '<option value="">Search Across All Notes</option>' +
      state.documents.map(d => `<option value="${d.id}">${escapeHtml(d.filename)}</option>`).join('');
    elements.docFilterSelect.value = currentVal;
  }

  function handleFileSelect(e) {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
  }

  async function uploadFiles(fileList) {
    if (!state.apiKeyConfigured) {
      showToast('Please configure your Gemini API Key before uploading documents.', 'error');
      openApiKeyModal();
      return;
    }

    const formData = new FormData();
    let validCount = 0;

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        formData.append('files', file);
        validCount++;
      } else {
        showToast(`Skipped '${file.name}': Only PDFs supported.`, 'error');
      }
    }

    if (validCount === 0) return;

    // Show processing UI
    elements.uploadStatus.classList.remove('hidden');
    elements.dropzoneTrigger.classList.add('hidden');
    elements.uploadStatusText.textContent = `Extracting & embedding ${validCount} PDF(s)...`;

    try {
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      if (data.uploaded_count > 0) {
        showToast(`Successfully indexed ${data.uploaded_count} academic document(s)!`, 'success');
      }

      if (data.errors && data.errors.length > 0) {
        data.errors.forEach(err => showToast(err, 'error'));
      }

      await fetchDocuments();
      await checkSystemHealth();
    } catch (err) {
      console.error('Upload error:', err);
      showToast(err.message || 'Error uploading files', 'error');
    } finally {
      elements.uploadStatus.classList.add('hidden');
      elements.dropzoneTrigger.classList.remove('hidden');
      elements.fileInput.value = '';
    }
  }

  window.deleteDocument = async function(docId, event) {
    event.stopPropagation();
    if (!confirm('Remove this document from the active knowledge base?')) return;

    try {
      const res = await fetch(`/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete document');
      showToast('Document removed from knowledge base.', 'info');
      await fetchDocuments();
    } catch (err) {
      console.error('Delete error:', err);
      showToast('Could not delete document', 'error');
    }
  };

  // =========================================================================
  // Chat & RAG Interaction
  // =========================================================================
  async function submitChatQuery(message) {
    if (!message.trim() || state.isLoading) return;

    // Clear input
    elements.chatInput.value = '';
    elements.chatInput.style.height = 'auto';

    // Hide welcome hero on first message
    elements.welcomeHero.classList.add('hidden');

    // Append user message
    appendUserMessage(message);
    state.messages.push({ role: 'user', content: message });

    // Show loading
    setLoadingState(true, 'Retrieving curriculum context...');

    try {
      // Dynamic loading text transition
      const timer1 = setTimeout(() => {
        if (state.isLoading) setLoadingState(true, 'Analyzing retrieved document chunks...');
      }, 1200);

      const timer2 = setTimeout(() => {
        if (state.isLoading) setLoadingState(true, 'Generating grounded answer with Gemini...');
      }, 2500);

      const payload = {
        message: message,
        study_mode: state.studyMode,
        doc_id: state.docFilter || null
      };

      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      clearTimeout(timer1);
      clearTimeout(timer2);

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to retrieve academic answer');
      }

      appendAiMessage(data);
      state.messages.push({ role: 'assistant', data: data });

    } catch (err) {
      console.error('Chat error:', err);
      appendErrorMessage(err.message || 'An error occurred while answering your question.');
    } finally {
      setLoadingState(false);
      scrollToBottom();
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row-user';
    row.innerHTML = `<div class="message-bubble-user">${escapeHtml(text)}</div>`;
    elements.chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendAiMessage(data) {
    const row = document.createElement('div');
    row.className = 'message-row-ai';

    const modeLabels = {
      general: 'General Q&A',
      summarize: 'Summary',
      eli5: 'Simple Explanation',
      exam: 'Exam Prep',
      revision: 'Revision Notes',
      quiz: 'Practice Quiz'
    };
    const modeName = modeLabels[data.study_mode] || 'Academic Answer';

    const groundedBadge = data.grounded
      ? `<span class="ai-tag grounded">📚 Document Grounded</span>`
      : `<span class="ai-tag general">🌐 General Knowledge</span>`;

    // Render citations if available
    let citationsHtml = '';
    if (data.citations && data.citations.length > 0) {
      citationsHtml = `
        <div class="citations-box">
          <div class="citations-header" onclick="this.parentElement.classList.toggle('open')">
            <span>📎 Verified Source Citations (${data.citations.length})</span>
            <svg class="citations-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="citations-list">
            ${data.citations.map(c => `
              <div class="citation-item">
                <div class="citation-top-row">
                  <span class="citation-doc-name">
                    📄 ${escapeHtml(c.document)}
                  </span>
                  <span class="citation-page-badge">Page ${c.page}</span>
                </div>
                <div class="citation-preview">"${escapeHtml(c.preview)}"</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    row.innerHTML = `
      <div class="ai-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a8 8 0 0 0-8 8c0 3.3 2 6.2 5 7.4V20a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2.6c3-1.2 5-4.1 5-7.4a8 8 0 0 0-8-8z"></path>
          <line x1="9.5" y1="9" x2="9.51" y2="9"></line><line x1="14.5" y1="9" x2="14.51" y2="9"></line>
        </svg>
      </div>
      <div class="message-card-ai">
        <div class="ai-header-bar">
          <div class="ai-tags">
            ${groundedBadge}
            <span class="ai-tag mode">${modeName}</span>
          </div>
          <button class="copy-btn" title="Copy answer" onclick="copyAnswerText(this)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>Copy</span>
          </button>
        </div>
        <div class="ai-body">${parseMarkdown(data.answer)}</div>
        ${citationsHtml}
      </div>
    `;

    elements.chatMessages.appendChild(row);

    // Apply syntax highlighting
    row.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
    });

    // Apply KaTeX math formula rendering if available
    if (window.renderMathInElement) {
      renderMathInElement(row.querySelector('.ai-body'), {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true }
        ],
        throwOnError: false
      });
    }

    scrollToBottom();
  }

  function appendErrorMessage(errorText) {
    const row = document.createElement('div');
    row.className = 'message-row-ai';
    row.innerHTML = `
      <div class="ai-avatar" style="background: var(--danger-color);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <div class="message-card-ai" style="border-color: rgba(239, 68, 68, 0.4);">
        <div class="ai-header-bar">
          <span class="ai-tag" style="background: rgba(239,68,68,0.15); color: #ef4444;">Error</span>
        </div>
        <div class="ai-body" style="color: #f87171;">${escapeHtml(errorText)}</div>
      </div>
    `;
    elements.chatMessages.appendChild(row);
    scrollToBottom();
  }

  function setLoadingState(isLoading, statusMsg = '') {
    state.isLoading = isLoading;
    if (isLoading) {
      elements.loadingBubble.classList.remove('hidden');
      elements.loadingStatusText.textContent = statusMsg;
      elements.sendBtn.disabled = true;
    } else {
      elements.loadingBubble.classList.add('hidden');
      elements.sendBtn.disabled = false;
    }
  }

  function scrollToBottom() {
    elements.messagesScroll.scrollTo({
      top: elements.messagesScroll.scrollHeight,
      behavior: 'smooth'
    });
  }

  function resetChat() {
    elements.chatMessages.innerHTML = '';
    elements.welcomeHero.classList.remove('hidden');
    state.messages = [];
    showToast('Conversation cleared.', 'info');
  }

  window.copyAnswerText = function(btn) {
    const card = btn.closest('.message-card-ai');
    const body = card.querySelector('.ai-body');
    if (!body) return;

    navigator.clipboard.writeText(body.innerText).then(() => {
      const origHtml = btn.innerHTML;
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span style="color: #10b981;">Copied!</span>
      `;
      setTimeout(() => btn.innerHTML = origHtml, 2000);
    }).catch(err => {
      console.error('Clipboard copy failed:', err);
    });
  };

  // =========================================================================
  // API Key Modal Management
  // =========================================================================
  function openApiKeyModal() {
    elements.apiModal.classList.remove('hidden');
    elements.modalFeedback.classList.add('hidden');
    elements.modalApiKeyInput.value = '';
    elements.modalApiKeyInput.focus();
  }

  function closeApiKeyModal() {
    elements.apiModal.classList.add('hidden');
  }

  async function saveApiKey() {
    const key = elements.modalApiKeyInput.value.trim();
    if (!key) {
      showModalFeedback('Please enter a valid Gemini API key.', 'error');
      return;
    }

    elements.modalSaveBtn.disabled = true;
    elements.modalSaveBtn.textContent = 'Verifying...';

    try {
      const res = await fetch('/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Invalid API key');

      state.apiKeyConfigured = true;
      updateStatusUI(true);
      showToast('Gemini API Key connected successfully!', 'success');
      closeApiKeyModal();
    } catch (err) {
      console.error('API key save error:', err);
      showModalFeedback(err.message || 'Failed to verify key', 'error');
    } finally {
      elements.modalSaveBtn.disabled = false;
      elements.modalSaveBtn.textContent = 'Save & Connect';
    }
  }

  function showModalFeedback(msg, type) {
    elements.modalFeedback.className = `modal-feedback ${type}`;
    elements.modalFeedback.textContent = msg;
    elements.modalFeedback.classList.remove('hidden');
  }

  // =========================================================================
  // Utility Functions
  // =========================================================================
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
      success: '✓',
      error: '✕',
      info: 'ℹ'
    };

    toast.innerHTML = `
      <span>${icons[type] || '•'}</span>
      <span>${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function parseMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(text);
    }
    return escapeHtml(text).replace(/\n/g, '<br/>');
  }

  function escapeHtml(string) {
    if (!string) return '';
    return String(string)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
