// ==================== STATE ====================
let extractedText = '';
let currentSummary = '';
let currentUser = null;

// ==================== DOM ELEMENTS ====================
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const removeFile = document.getElementById('removeFile');
const statsSection = document.getElementById('statsSection');
const originalText = document.getElementById('originalText');
const wordSlider = document.getElementById('wordSlider');
const wordTarget = document.getElementById('wordTarget');
const summarizeBtn = document.getElementById('summarizeBtn');
const summaryResult = document.getElementById('summaryResult');
const summaryText = document.getElementById('summaryText');
const loading = document.getElementById('loading');
const loadingMsg = document.getElementById('loadingMsg');
const toast = document.getElementById('toast');
const themeToggle = document.getElementById('themeToggle');

// ==================== AUTH CHECK ====================
async function checkAuth() {
    try {
        const response = await fetch('/auth/me');
        const data = await response.json();
        
        if (data.logged_in && data.user) {
            currentUser = data.user;
            showLoggedInState();
        } else {
            currentUser = null;
            showGuestState();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showGuestState();
    }
}

function showLoggedInState() {
    const loginBtn = document.getElementById('loginBtn');
    const userMenu = document.getElementById('userMenu');
    const guestBanner = document.getElementById('guestBanner');
    const userAvatar = document.getElementById('userAvatar');
    const userName = document.getElementById('userName');
    
    if (loginBtn) loginBtn.classList.add('hidden');
    if (userMenu) userMenu.classList.remove('hidden');
    if (guestBanner) guestBanner.classList.add('hidden');
    
    if (currentUser) {
        if (userAvatar) userAvatar.textContent = currentUser.username.charAt(0).toUpperCase();
        if (userName) userName.textContent = currentUser.username;
    }
}

function showGuestState() {
    const loginBtn = document.getElementById('loginBtn');
    const userMenu = document.getElementById('userMenu');
    const guestBanner = document.getElementById('guestBanner');
    
    if (loginBtn) loginBtn.classList.remove('hidden');
    if (userMenu) userMenu.classList.add('hidden');
    
    // Vérifier si la bannière a été fermée dans cette session
    if (guestBanner && !sessionStorage.getItem('guestBannerClosed')) {
        guestBanner.classList.remove('hidden');
    }
}

// User dropdown toggle
document.getElementById('userBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('userDropdown')?.classList.toggle('show');
});

// Close dropdown when clicking outside
document.addEventListener('click', () => {
    document.getElementById('userDropdown')?.classList.remove('show');
});

// Close guest banner
document.getElementById('closeBanner')?.addEventListener('click', () => {
    document.getElementById('guestBanner')?.classList.add('hidden');
    sessionStorage.setItem('guestBannerClosed', 'true');
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
        await fetch('/auth/logout', { method: 'POST' });
        currentUser = null;
        showGuestState();
        showToast('Déconnexion réussie', 'success');
    } catch (error) {
        showToast('Erreur lors de la déconnexion', 'error');
    }
});

// Check auth on page load
checkAuth();

// ==================== THEME ====================
// Initialiser les icônes du thème au chargement
function initThemeIcons() {
    const savedTheme = localStorage.getItem('nectar-theme') || 'dark';
    const isDark = savedTheme === 'dark';
    document.querySelector('.icon-sun')?.classList.toggle('hidden', !isDark);
    document.querySelector('.icon-moon')?.classList.toggle('hidden', isDark);
}
initThemeIcons();

themeToggle.addEventListener('click', () => {
    const isDark = document.body.classList.contains('dark-mode');
    document.body.classList.toggle('dark-mode', !isDark);
    document.body.classList.toggle('light-mode', isDark);
    localStorage.setItem('nectar-theme', isDark ? 'light' : 'dark');
    document.querySelector('.icon-sun')?.classList.toggle('hidden', isDark);
    document.querySelector('.icon-moon')?.classList.toggle('hidden', !isDark);
});

// ==================== TABS ====================
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
});

// ==================== FILE UPLOAD ====================
uploadBox.addEventListener('click', () => fileInput.click());
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});
uploadBox.addEventListener('dragleave', () => uploadBox.classList.remove('drag-over'));
uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFileUpload(e.dataTransfer.files[0]);
    }
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFileUpload(e.target.files[0]);
});
removeFile.addEventListener('click', resetFile);

function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading('Extraction du texte...');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            extractedText = data.text;
            originalText.value = data.text;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            uploadBox.classList.add('hidden');
            fileInfo.classList.remove('hidden');
            statsSection.classList.remove('hidden');
            updateStats(data.stats);
            showToast('Document extrait avec succès', 'success');
        } else {
            showToast(data.error || 'Erreur lors de l\'extraction', 'error');
        }
    })
    .catch(err => {
        hideLoading();
        showToast('Erreur de connexion', 'error');
    });
}

function resetFile() {
    extractedText = '';
    originalText.value = '';
    fileInput.value = '';
    uploadBox.classList.remove('hidden');
    fileInfo.classList.add('hidden');
    statsSection.classList.add('hidden');
    summaryResult.classList.add('hidden');
}

function updateStats(stats) {
    document.getElementById('statWords').textContent = stats.word_count || 0;
    document.getElementById('statChars').textContent = stats.char_count || 0;
    document.getElementById('statSentences').textContent = stats.sentence_count || 0;
    document.getElementById('statTime').textContent = stats.reading_time || 0;
}

// ==================== SLIDER ====================
wordSlider.addEventListener('input', () => {
    wordTarget.textContent = `${wordSlider.value} mots`;
});

// ==================== SUMMARIZE ====================
summarizeBtn.addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) {
        showToast('Veuillez entrer ou uploader du texte', 'error');
        return;
    }
    
    const style = document.getElementById('summaryStyle').value;
    showLoading('Génération du résumé avec OpenAI...');
    
    fetch('/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            target_words: parseInt(wordSlider.value),
            style: style
        })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            currentSummary = data.summary;
            summaryText.value = data.summary;
            document.getElementById('resultWords').textContent = `${data.summary_stats.word_count} mots`;
            const compression = Math.round((1 - data.summary_stats.word_count / text.split(' ').length) * 100);
            document.getElementById('resultCompression').textContent = `${compression}% réduit`;
            document.getElementById('resultMethod').textContent = data.method === 'openai' ? 'OpenAI' : 'Extractif';
            summaryResult.classList.remove('hidden');
            showToast('Résumé généré avec succès', 'success');
            
            // Rafraîchir l'historique si connecté
            if (currentUser) {
                loadHistory();
            }
        } else {
            showToast(data.error || 'Erreur lors du résumé', 'error');
        }
    })
    .catch(err => {
        hideLoading();
        showToast('Erreur de connexion', 'error');
    });
});

// ==================== COPY & DOWNLOAD ====================
document.getElementById('copySummary').addEventListener('click', () => {
    navigator.clipboard.writeText(summaryText.value);
    showToast('Copié dans le presse-papiers', 'success');
});

document.getElementById('downloadSummary').addEventListener('click', () => {
    const blob = new Blob([summaryText.value], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'resume.txt';
    a.click();
    URL.revokeObjectURL(url);
});

document.getElementById('clearText').addEventListener('click', () => {
    originalText.value = '';
    extractedText = '';
});

// ==================== TRANSLATE MODAL ====================
const translateModal = document.getElementById('translateModal');
document.getElementById('translateSummary').addEventListener('click', () => {
    translateModal.classList.remove('hidden');
});
document.getElementById('closeTranslateModal').addEventListener('click', () => {
    translateModal.classList.add('hidden');
});
document.getElementById('closeModalBtn').addEventListener('click', () => {
    translateModal.classList.add('hidden');
});
document.getElementById('doTranslate').addEventListener('click', () => {
    const lang = document.getElementById('modalTargetLang').value;
    showLoading('Traduction en cours...');
    
    fetch('/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: currentSummary, target_language: lang })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            document.getElementById('modalTranslation').textContent = data.translation;
        } else {
            showToast('Erreur de traduction', 'error');
        }
    });
});

// ==================== ANALYZE TAB ====================

// Keywords
document.getElementById('extractKeywords').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Extraction des mots-clés...');
    fetch('/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, count: 10 })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const container = document.getElementById('keywordsContainer');
            container.innerHTML = data.keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('');
        }
    });
});

// Sentiment
document.getElementById('analyzeSentiment').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Analyse du sentiment...');
    fetch('/sentiment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const emoji = data.sentiment === 'positif' ? '😊' : data.sentiment === 'négatif' ? '😔' : '😐';
            const container = document.getElementById('sentimentResult');
            container.innerHTML = `
                <div class="sentiment-emoji">${emoji}</div>
                <div class="sentiment-label">${data.sentiment.charAt(0).toUpperCase() + data.sentiment.slice(1)}</div>
                <div class="sentiment-score">Score: ${data.score}</div>
                <div class="sentiment-emotions">
                    ${(data.emotions || []).map(e => `<span class="emotion-tag">${e}</span>`).join('')}
                </div>
                <p style="margin-top: 0.75rem; font-size: 0.85rem; color: var(--text-dim)">${data.tone || ''}</p>
            `;
        }
    });
});

// Word Cloud
document.getElementById('generateWordCloud').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Génération du nuage de mots...');
    fetch('/wordcloud', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, max_words: 40 })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const container = document.getElementById('wordcloudContainer');
            container.innerHTML = data.words.map(w => 
                `<span class="word-item" style="font-size: ${Math.max(12, w.size / 3)}px; opacity: ${0.5 + w.size/200}">${w.text}</span>`
            ).join(' ');
        }
    });
});

// Titles
document.getElementById('generateTitles').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Génération des titres...');
    fetch('/generate-title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, count: 5 })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const container = document.getElementById('titlesContainer');
            container.innerHTML = data.titles.map((t, i) => `
                <div class="title-item" onclick="navigator.clipboard.writeText('${t.replace(/'/g, "\\'")}'); showToast('Titre copié', 'success')">
                    <span class="title-number">${i + 1}</span>
                    <span class="title-text">${t}</span>
                </div>
            `).join('');
        }
    });
});

// Advanced Stats
document.getElementById('getAdvancedStats').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Calcul des statistiques...');
    fetch('/advanced-stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const container = document.getElementById('advancedStats');
            container.innerHTML = `
                <div class="adv-stat"><span class="adv-stat-value">${data.words}</span><span class="adv-stat-label">Mots</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.sentences}</span><span class="adv-stat-label">Phrases</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.paragraphs}</span><span class="adv-stat-label">Paragraphes</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.unique_words}</span><span class="adv-stat-label">Mots uniques</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.avg_word_length}</span><span class="adv-stat-label">Long. moy. mot</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.avg_sentence_length}</span><span class="adv-stat-label">Mots/phrase</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.reading_time_minutes} min</span><span class="adv-stat-label">Temps lecture</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.complexity}</span><span class="adv-stat-label">Complexité</span></div>
                <div class="adv-stat"><span class="adv-stat-value">${data.characters_no_spaces}</span><span class="adv-stat-label">Caractères</span></div>
            `;
        }
    });
});

// ==================== TOOLS TAB ====================

// Q&A
document.getElementById('askQuestion').addEventListener('click', () => {
    const text = originalText.value.trim();
    const question = document.getElementById('questionInput').value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    if (!question) { showToast('Posez une question', 'error'); return; }
    
    showLoading('Recherche de la réponse...');
    fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, question })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            document.getElementById('qaAnswer').innerHTML = `<p>${data.answer}</p>`;
        } else {
            showToast('Erreur', 'error');
        }
    });
});

// Translate
document.getElementById('translateText').addEventListener('click', () => {
    const text = originalText.value.trim();
    const lang = document.getElementById('targetLanguage').value;
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Traduction en cours...');
    fetch('/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_language: lang })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            document.getElementById('translationResult').innerHTML = `<p>${data.translation}</p>`;
        } else {
            showToast('Erreur de traduction', 'error');
        }
    });
});

// Sections
document.getElementById('summarizeSections').addEventListener('click', () => {
    const text = originalText.value.trim();
    if (!text) { showToast('Texte requis', 'error'); return; }
    
    showLoading('Analyse des sections...');
    fetch('/summarize-sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, words_per_section: 50 })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            const container = document.getElementById('sectionsResult');
            container.innerHTML = data.sections.map(s => `
                <div class="section-item">
                    <div class="section-title">${s.title}</div>
                    <div class="section-summary">${s.summary}</div>
                </div>
            `).join('');
        }
    });
});

// ==================== UTILITIES ====================

function showLoading(msg = 'Traitement...') {
    loadingMsg.textContent = msg;
    loading.classList.remove('hidden');
}

function hideLoading() {
    loading.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const toastEl = document.getElementById('toast');
    const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" style="color: var(--accent)"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" style="color: var(--danger)"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" style="color: var(--primary)"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    
    document.getElementById('toastIcon').innerHTML = icons[type] || icons.info;
    document.getElementById('toastMsg').textContent = message;
    toastEl.className = `toast toast-${type} show`;
    
    setTimeout(() => {
        toastEl.classList.remove('show');
    }, 3000);
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Enter key for question
document.getElementById('questionInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('askQuestion').click();
});

// ==================== HISTORIQUE ====================

async function loadHistory() {
    if (!currentUser) {
        document.getElementById('historyList').innerHTML = '<p class="empty-state">Connectez-vous pour voir votre historique</p>';
        return;
    }
    
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        
        console.log('Historique reçu:', data);
        
        if (data.success && data.history && data.history.length > 0) {
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = data.history.map(item => `
                <div class="history-item" data-id="${item.id}">
                    <div class="history-item-header">
                        <span class="history-filename">${item.filename || 'Sans titre'}</span>
                        <span class="history-date">${formatDate(item.created_at)}</span>
                    </div>
                    <div class="history-preview">${item.summary ? item.summary.substring(0, 80) + '...' : ''}</div>
                    <div class="history-meta">
                        <span>${item.original_words || 0} → ${item.summary_words || 0} mots</span>
                        <span class="history-badge">${item.style || 'paragraph'}</span>
                    </div>
                </div>
            `).join('');
            
            // Click sur un item pour le charger
            document.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', () => loadHistoryItem(item.dataset.id));
            });
        } else {
            document.getElementById('historyList').innerHTML = '<p class="empty-state">Aucun historique</p>';
        }
    } catch (error) {
        console.error('Erreur chargement historique:', error);
        document.getElementById('historyList').innerHTML = '<p class="empty-state">Erreur de chargement</p>';
    }
}

async function loadHistoryItem(id) {
    try {
        const response = await fetch(`/api/history/${id}`);
        const data = await response.json();
        
        if (response.status === 401) {
            showToast('Veuillez vous connecter pour accéder à l\'historique', 'error');
            return;
        }
        
        if (data.success && data.summary) {
            // Charger le texte original et le résumé
            if (data.summary.original_text) {
                originalText.value = data.summary.original_text;
                extractedText = data.summary.original_text;
                
                // Mettre à jour les stats du texte original
                const words = data.summary.original_text.trim().split(/\s+/).filter(w => w).length;
                const chars = data.summary.original_text.length;
                document.getElementById('statWords').textContent = words;
                document.getElementById('statChars').textContent = chars;
            }
            
            summaryText.textContent = data.summary.summary;
            summaryResult.classList.remove('hidden');
            currentSummary = data.summary.summary;
            
            // Mettre à jour les stats du résumé
            document.getElementById('summaryWords').textContent = data.summary.summary_words || 0;
            
            showToast('Résumé chargé depuis l\'historique', 'success');
            
            // Aller à l'onglet résumé
            document.querySelector('[data-tab="summarize"]').click();
        } else {
            showToast(data.error || 'Résumé non trouvé', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showToast('Erreur lors du chargement', 'error');
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'À l\'instant';
    if (diff < 3600000) return `Il y a ${Math.floor(diff / 60000)} min`;
    if (diff < 86400000) return `Il y a ${Math.floor(diff / 3600000)}h`;
    
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

// Charger l'historique au démarrage et après connexion
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(loadHistory, 500); // Attendre que checkAuth soit terminé
});

// Bouton pour voir l'historique
document.getElementById('showHistory')?.addEventListener('click', (e) => {
    e.preventDefault();
    loadHistory();
    showToast('Historique mis à jour', 'info');
});
