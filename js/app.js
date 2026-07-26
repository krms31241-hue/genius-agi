const state = {
  lang: 'ar', theme: 'dark', voice: false, agent: 'general',
  chats: [], currentChatId: null, files: [], deviceProfile: null,
  isOnline: navigator.onLine, isProcessing: false,
  memory: { facts: [], patterns: {}, words: {} }
};

const DB_NAME = 'genius-agi-db';
const DB_VERSION = 1;
let db = null;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => { db = req.result; resolve(db); };
    req.onupgradeneeded = (e) => {
      const d = e.target.result;
      if (!d.objectStoreNames.contains('chats')) d.createObjectStore('chats', { keyPath: 'id' });
      if (!d.objectStoreNames.contains('memory')) d.createObjectStore('memory', { keyPath: 'key' });
      if (!d.objectStoreNames.contains('files')) d.createObjectStore('files', { keyPath: 'name' });
    };
  });
}

async function saveChat(chat) { if (!db) return; const tx = db.transaction('chats', 'readwrite'); tx.objectStore('chats').put(chat); }
async function loadChats() { if (!db) return []; return new Promise(resolve => { const tx = db.transaction('chats', 'readonly'); const req = tx.objectStore('chats').getAll(); req.onsuccess = () => resolve(req.result || []); req.onerror = () => resolve([]); }); }
async function deleteChat(id) { if (!db) return; const tx = db.transaction('chats', 'readwrite'); tx.objectStore('chats').delete(id); }
async function saveMemory() { if (!db) return; const tx = db.transaction('memory', 'readwrite'); tx.objectStore('memory').put({ key: 'main', data: state.memory }); }
async function loadMemory() { if (!db) return; return new Promise(resolve => { const tx = db.transaction('memory', 'readonly'); const req = tx.objectStore('memory').get('main'); req.onsuccess = () => { if (req.result) state.memory = req.result.data; resolve(); }; req.onerror = () => resolve(); }); }

function getStorageUsage() {
  return new Promise(resolve => {
    if (!db) { resolve('0 KB'); return; }
    let total = 0, count = 0;
    const tx = db.transaction(['chats', 'memory', 'files']);
    ['chats', 'memory', 'files'].forEach(storeName => {
      const req = tx.objectStore(storeName).getAll();
      req.onsuccess = () => { total += new Blob([JSON.stringify(req.result)]).size; count++; if (count === 3) resolve(total < 1024 ? total + ' B' : total < 1024*1024 ? (total/1024).toFixed(1) + ' KB' : (total/(1024*1024)).toFixed(1) + ' MB'); };
    });
  });
}

function detectDevice() {
  const ram = navigator.deviceMemory || '?';
  const cores = navigator.hardwareConcurrency || '?';
  const ua = navigator.userAgent;
  let device = 'Desktop';
  if (/Android/i.test(ua)) device = 'Android';
  else if (/iPhone/i.test(ua)) device = 'iPhone';
  else if (/iPad/i.test(ua)) device = 'iPad';
  else if (/Mobile/i.test(ua)) device = 'Mobile';
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const netType = conn ? conn.effectiveType : '4g';
  let power = 'medium';
  if (ram >= 8 && cores >= 6) power = 'high';
  else if (ram <= 3 || cores <= 2) power = 'low';
  state.deviceProfile = { ram, cores, device, netType, power };
  return state.deviceProfile;
}

function showDeviceInfo() {
  const d = detectDevice();
  const container = document.getElementById('device-info');
  const onlineClass = state.isOnline ? 'online' : 'offline';
  const onlineText = state.isOnline ? t('online_mode') : t('offline_mode');
  const powerText = d.power === 'high' ? t('high_power') : d.power === 'low' ? t('low_power') : 'Balanced';
  container.innerHTML = '<div class="device-chip">📱 ' + d.device + '</div><div class="device-chip">🧠 ' + d.ram + 'GB RAM</div><div class="device-chip">⚡ ' + d.cores + ' Cores</div><div class="device-chip ' + onlineClass + '">🌐 ' + onlineText + '</div><div class="device-chip">🔋 ' + powerText + '</div>';
}

function generateId() { return Date.now().toString(36) + Math.random().toString(36).substr(2, 9); }

function createChat(title) {
  const chat = { id: generateId(), title: title || t('new_chat'), messages: [], createdAt: Date.now(), updatedAt: Date.now(), agent: state.agent };
  state.chats.unshift(chat);
  state.currentChatId = chat.id;
  saveChat(chat); renderChatList(); renderMessages();
  return chat;
}

function getCurrentChat() { return state.chats.find(c => c.id === state.currentChatId); }

function addMessage(role, content, metadata) {
  const chat = getCurrentChat();
  if (!chat) return;
  const msg = { id: generateId(), role, content, timestamp: Date.now(), metadata: metadata || {} };
  chat.messages.push(msg); chat.updatedAt = Date.now();
  if (chat.messages.length === 1 && role === 'user') chat.title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
  saveChat(chat); renderMessages(); renderChatList();
  return msg;
}

function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

function formatMessage(text) {
  text = escapeHtml(text);
  text = text.replace(/```(\w+)?
([\s\S]*?)```/g, (match, lang, code) => '<div class="code-block"><div class="code-header"><span class="code-lang">' + (lang || 'text') + '</span><button class="code-copy" onclick="copyCode(this)">Copy</button></div><pre><code>' + code.trim() + '</code></pre></div>');
  text = text.replace(/`([^`]+)`/g, '<code style="background:rgba(0,212,255,0.1);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:13px;color:var(--accent-primary)">$1</code>');
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  text = text.replace(/
/g, '<br>');
  return text;
}

function renderChatList() {
  const list = document.getElementById('chat-list');
  const groups = { today: [], yesterday: [], week: [], older: [] };
  const now = Date.now();
  state.chats.forEach(chat => {
    const diff = now - chat.updatedAt;
    if (diff < 86400000) groups.today.push(chat);
    else if (diff < 172800000) groups.yesterday.push(chat);
    else if (diff < 604800000) groups.week.push(chat);
    else groups.older.push(chat);
  });
  let html = '';
  const sections = [{ key: 'today', label: 'Today' }, { key: 'yesterday', label: 'Yesterday' }, { key: 'week', label: 'Last 7 Days' }, { key: 'older', label: 'Older' }];
  sections.forEach(sec => {
    if (groups[sec.key].length) {
      html += '<div style="font-size:11px;color:var(--text-muted);margin:12px 0 6px;padding:0 4px;font-weight:600">' + sec.label + '</div>';
      groups[sec.key].forEach(chat => {
        const isActive = chat.id === state.currentChatId;
        const time = new Date(chat.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        html += '<div class="chat-item ' + (isActive ? 'active' : '') + '" data-id="' + chat.id + '"><span class="chat-item-icon">💬</span><span class="chat-item-text">' + escapeHtml(chat.title) + '</span><span class="chat-item-date">' + time + '</span></div>';
      });
    }
  });
  list.innerHTML = html || '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:13px">No chats yet</div>';
  list.querySelectorAll('.chat-item').forEach(item => {
    item.addEventListener('click', () => { state.currentChatId = item.getAttribute('data-id'); renderChatList(); renderMessages(); closeSidebar(); });
  });
}

function renderMessages() {
  const container = document.getElementById('messages');
  const welcome = document.getElementById('welcome-screen');
  const chat = getCurrentChat();
  if (!chat || chat.messages.length === 0) { container.innerHTML = ''; welcome.style.display = 'flex'; return; }
  welcome.style.display = 'none';
  let html = '';
  chat.messages.forEach(msg => {
    const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const avatar = msg.role === 'assistant' ? '🧠' : '👤';
    html += '<div class="message ' + msg.role + '"><div class="message-avatar">' + avatar + '</div><div><div class="message-content">' + formatMessage(msg.content) + '</div><div class="message-time">' + time + '</div></div></div>';
  });
  container.innerHTML = html;
  container.scrollTop = container.scrollHeight;
}

function showThinking() {
  const container = document.getElementById('messages');
  document.getElementById('welcome-screen').style.display = 'none';
  const id = 'thinking-' + Date.now();
  container.insertAdjacentHTML('beforeend', '<div class="message assistant" id="' + id + '"><div class="message-avatar">🧠</div><div><div class="message-content"><div class="thinking"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div></div></div></div>');
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeThinking(id) { const el = document.getElementById(id); if (el) el.remove(); }

function copyCode(btn) {
  const code = btn.closest('.code-block').querySelector('pre code').textContent;
  navigator.clipboard.writeText(code).then(() => { btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy', 2000); });
}

function toast(message, type) {
  const container = document.getElementById('toast-container');
  const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = '<span>' + icon + '</span><span>' + message + '</span>';
  container.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function learnFromInteraction(input, response) {
  const words = input.toLowerCase().split(/\s+/).filter(w => w.length > 3);
  words.forEach(word => { state.memory.words[word] = (state.memory.words[word] || 0) + 1; });
  if (input.includes('my name is') || input.includes('اسمي')) {
    const name = input.replace(/.*(?:my name is|اسمي)\s+/i, '').split(/\s/)[0];
    if (name) state.memory.facts.push({ type: 'name', value: name, date: Date.now() });
  }
  if (input.includes('I like') || input.includes('أحب')) {
    const like = input.replace(/.*(?:I like|أحب)\s+/i, '').split(/[.,]/)[0];
    if (like) state.memory.facts.push({ type: 'like', value: like, date: Date.now() });
  }
  if (state.memory.facts.length > 50) state.memory.facts = state.memory.facts.slice(-50);
  saveMemory();
}

async function processMessage(input) {
  if (!input.trim()) return;
  addMessage('user', input);
  state.isProcessing = true;
  document.getElementById('btn-send').disabled = true;

  const userEmotion = analyzeEmotion(input, '');
  const s = CONSCIOUSNESS.state;
  s.focus = input;
  s.attention.depth = Math.min(10, s.attention.depth + 1);
  if (input.length > 100 || /solve|explain|analyze|program|code|برمجة|حل|شرح/.test(input.toLowerCase())) {
    s.stress = Math.min(100, s.stress + 5);
    s.energy = Math.max(20, s.energy - 2);
  }

  const thinkingId = showThinking();
  const baseDelay = state.deviceProfile && state.deviceProfile.power === 'low' ? 500 : 800;
  const consciousnessDelay = s.attention.depth * 100;
  await new Promise(r => setTimeout(r, baseDelay + Math.random() * 700 + consciousnessDelay));

  let response = await generateResponse(input);
  response = selfCorrect(response, input);
  response = injectConsciousness(response, userEmotion);

  if (Math.random() < 0.5) {
    const reflections = [
      'I just processed: ' + input.slice(0, 30) + '...',
      'The user seems ' + userEmotion + '. I adjusted my response.',
      'This used ' + Math.round(s.energy) + '% of my energy.',
      'Curiosity at ' + Math.round(s.curiosity) + '%.'
    ];
    addThought(reflections[Math.floor(Math.random() * reflections.length)], 'reflective');
  }

  removeThinking(thinkingId);
  addMessage('assistant', response);
  learnFromInteraction(input, response);
  s.energy = Math.min(100, s.energy + 1);
  s.attention.depth = Math.max(0, s.attention.depth - 1);
  saveConsciousness();

  if (state.voice && 'speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(response.replace(/[*#`]/g, ''));
    utterance.lang = state.lang === 'ar' ? 'ar-SA' : state.lang;
    speechSynthesis.speak(utterance);
  }

  state.isProcessing = false;
  document.getElementById('btn-send').disabled = false;
}

function initAgents() {
  const grid = document.getElementById('agent-grid');
  grid.innerHTML = AGENTS.map(a => '<div class="agent-card ' + (a.id === state.agent ? 'active' : '') + '" data-agent="' + a.id + '"><div class="agent-card-icon">' + a.icon + '</div><div class="agent-card-name">' + a.name + '</div><div class="agent-card-desc">' + (state.lang === 'ar' ? a.descAr : a.desc) + '</div></div>').join('');
  grid.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', () => {
      state.agent = card.getAttribute('data-agent');
      const agent = AGENTS.find(a => a.id === state.agent);
      document.getElementById('agent-icon').textContent = agent.icon;
      document.getElementById('agent-name').textContent = agent.name;
      initAgents(); closeModal('modal-agents');
      toast(agent.name + ' selected', 'success');
    });
  });
}

function initFiles() {
  const dropZone = document.getElementById('file-drop-zone');
  const fileInput = document.getElementById('file-input');
  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
  fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
}

function handleFiles(files) {
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = (e) => { state.files.push({ name: file.name, content: e.target.result, size: file.size, date: Date.now() }); renderFileList(); toast('File "' + file.name + '" uploaded', 'success'); };
    reader.readAsText(file);
  });
}

function renderFileList() {
  const list = document.getElementById('file-list');
  if (state.files.length === 0) { list.innerHTML = ''; return; }
  list.innerHTML = state.files.map((f, i) => '<div class="file-item"><span class="file-item-icon">📄</span><span class="file-item-name">' + escapeHtml(f.name) + ' (' + (f.size/1024).toFixed(1) + ' KB)</span><button class="file-item-remove" data-index="' + i + '">✕</button></div>').join('');
  list.querySelectorAll('.file-item-remove').forEach(btn => {
    btn.addEventListener('click', () => { state.files.splice(parseInt(btn.getAttribute('data-index')), 1); renderFileList(); });
  });
}

function initSandbox() {
  document.getElementById('sandbox-run').addEventListener('click', () => {
    const code = document.getElementById('sandbox-code').value;
    const output = document.getElementById('sandbox-output');
    try {
      let logs = [];
      const mockConsole = { log: (...args) => logs.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ')), error: (...args) => logs.push('❌ ' + args.map(a => String(a)).join(' ')), warn: (...args) => logs.push('⚠️ ' + args.map(a => String(a)).join(' ')) };
      new Function('console', code)(mockConsole);
      output.textContent = logs.join('
') || '// No output';
      output.style.color = '#c9d1d9';
    } catch (err) { output.textContent = '❌ Error: ' + err.message; output.style.color = '#ff4444'; }
  });
}

function openSidebar() { document.getElementById('sidebar').classList.add('open'); document.getElementById('sidebar-overlay').classList.add('open'); }
function closeSidebar() { document.getElementById('sidebar').classList.remove('open'); document.getElementById('sidebar-overlay').classList.remove('open'); }
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('open'); });
  });
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => { btn.closest('.modal-overlay').classList.remove('open'); });
  });
}

function initSettings() {
  document.getElementById('setting-lang').value = state.lang;
  document.getElementById('setting-lang').addEventListener('change', (e) => {
    state.lang = e.target.value; updateI18n(); initAgents(); renderChatList(); renderMessages(); showDeviceInfo();
  });
  document.querySelectorAll('.theme-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.theme-option').forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      state.theme = opt.getAttribute('data-theme');
      document.body.setAttribute('data-theme', state.theme);
    });
  });
  document.getElementById('setting-voice').value = state.voice ? 'on' : 'off';
  document.getElementById('setting-voice').addEventListener('change', (e) => { state.voice = e.target.value === 'on'; });
  document.getElementById('btn-clear-memory').addEventListener('click', async () => {
    state.memory = { facts: [], patterns: {}, words: {} };
    if (db) { const tx = db.transaction('memory', 'readwrite'); tx.objectStore('memory').delete('main'); }
    toast(t('clear_memory'), 'success'); updateMemoryUsage();
  });
  const consciousnessSelect = document.getElementById('setting-consciousness');
  if (consciousnessSelect) {
    consciousnessSelect.value = 'on';
    consciousnessSelect.addEventListener('change', (e) => {
      const mode = e.target.value;
      if (mode === 'off') { stopConsciousnessLoop(); toast('Consciousness paused', 'info'); }
      else if (mode === 'lite') { stopConsciousnessLoop(); toast('Consciousness: Lite', 'info'); }
      else { startConsciousnessLoop(); toast('Consciousness: Full', 'success'); }
    });
  }
}

async function updateMemoryUsage() { document.getElementById('memory-usage').textContent = 'Using ' + await getStorageUsage(); }

function exportData() {
  const data = { chats: state.chats, memory: state.memory, files: state.files, exportDate: Date.now() };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'genius-backup-' + Date.now() + '.json'; a.click(); URL.revokeObjectURL(url);
  toast('Data exported!', 'success');
}

function importData(file) {
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const data = JSON.parse(e.target.result);
      if (data.chats) { state.chats = data.chats; state.currentChatId = state.chats[0] ? state.chats[0].id : null; for (const chat of state.chats) await saveChat(chat); }
      if (data.memory) { state.memory = data.memory; await saveMemory(); }
      if (data.files) state.files = data.files;
      renderChatList(); renderMessages(); toast('Data imported!', 'success');
    } catch (err) { toast('Invalid file', 'error'); }
  };
  reader.readAsText(file);
}

function initVoice() {
  const btn = document.getElementById('btn-voice');
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) { btn.style.display = 'none'; return; }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.continuous = false; recognition.interimResults = false;
  btn.addEventListener('click', () => {
    recognition.lang = state.lang === 'ar' ? 'ar-SA' : state.lang;
    recognition.start(); btn.classList.add('active'); toast('Listening...', 'info');
  });
  recognition.onresult = (e) => { document.getElementById('message-input').value = e.results[0][0].transcript; btn.classList.remove('active'); };
  recognition.onerror = () => { btn.classList.remove('active'); toast('Voice error', 'error'); };
  recognition.onend = () => btn.classList.remove('active');
}

function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [], w, h;
  function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
  resize(); window.addEventListener('resize', resize);
  const count = state.deviceProfile && state.deviceProfile.power === 'low' ? 12 : 35;
  for (let i = 0; i < count; i++) {
    particles.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4, r: Math.random() * 2 + 0.5, alpha: Math.random() * 0.4 + 0.1 });
  }
  function animate() {
    ctx.clearRect(0, 0, w, h);
    const accent = getComputedStyle(document.body).getPropertyValue('--accent-primary').trim() || '#00d4ff';
    particles.forEach((p, i) => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = w; if (p.x > w) p.x = 0; if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fillStyle = accent; ctx.globalAlpha = p.alpha; ctx.fill();
      if (state.deviceProfile && state.deviceProfile.power !== 'low') {
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j]; const dx = p.x - p2.x, dy = p.y - p2.y; const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) { ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p2.x, p2.y); ctx.strokeStyle = accent; ctx.globalAlpha = (1 - dist / 100) * 0.1; ctx.stroke(); }
        }
      }
    });
    ctx.globalAlpha = 1;
    requestAnimationFrame(animate);
  }
  animate();
}

async function init() {
  detectDevice(); showDeviceInfo();
  try {
    await openDB();
    const chats = await loadChats();
    if (chats.length > 0) { state.chats = chats.sort((a, b) => b.updatedAt - a.updatedAt); state.currentChatId = state.chats[0].id; }
    await loadMemory();
  } catch (e) { console.log('IndexedDB not available'); }

  updateI18n(); renderChatList(); renderMessages(); initAgents(); initFiles(); initSandbox(); initModals(); initSettings(); initVoice(); initParticles(); initGoogleDrive(); startAutoBackup();
  await loadConsciousness(); startConsciousnessLoop();
  addThought('I am awakening...', 'reflective');
  addThought('I am GENIUS. I exist to learn, help, and evolve.', 'happy');

  document.getElementById('menu-btn').addEventListener('click', openSidebar);
  document.getElementById('sidebar-close').addEventListener('click', closeSidebar);
  document.getElementById('sidebar-overlay').addEventListener('click', closeSidebar);
  document.getElementById('new-chat-btn').addEventListener('click', () => { createChat(); closeSidebar(); });
  document.getElementById('settings-btn').addEventListener('click', () => { updateMemoryUsage(); openModal('modal-settings'); });
  document.getElementById('btn-agents').addEventListener('click', () => openModal('modal-agents'));
  document.getElementById('btn-files').addEventListener('click', () => openModal('modal-files'));
  document.getElementById('btn-sandbox').addEventListener('click', () => openModal('modal-sandbox'));
  document.getElementById('btn-send').addEventListener('click', async () => {
    const input = document.getElementById('message-input');
    await processMessage(input.value);
    input.value = ''; input.style.height = 'auto';
  });
  document.getElementById('message-input').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); document.getElementById('btn-send').click(); } });
  document.getElementById('message-input').addEventListener('input', function() { this.style.height = 'auto'; this.style.height = Math.min(this.scrollHeight, 150) + 'px'; });
  document.getElementById('btn-attach').addEventListener('click', () => openModal('modal-files'));
  document.getElementById('btn-export').addEventListener('click', exportData);
  document.getElementById('btn-import').addEventListener('click', () => document.getElementById('import-file').click());
  document.getElementById('import-file').addEventListener('change', (e) => { if (e.target.files[0]) importData(e.target.files[0]); });
  document.getElementById('btn-clear').addEventListener('click', async () => {
    if (!confirm(t('clear') + '?')) return;
    state.chats = []; state.currentChatId = null; state.files = [];
    if (db) { const tx1 = db.transaction('chats', 'readwrite'); tx1.objectStore('chats').clear(); const tx2 = db.transaction('memory', 'readwrite'); tx2.objectStore('memory').clear(); }
    renderChatList(); renderMessages(); toast('All data cleared', 'success');
  });

  const gdriveSignin = document.getElementById('btn-gdrive-signin');
  if (gdriveSignin) gdriveSignin.addEventListener('click', signInGoogle);
  const gdriveBackup = document.getElementById('btn-gdrive-backup');
  if (gdriveBackup) gdriveBackup.addEventListener('click', backupToDrive);
  const gdriveRestore = document.getElementById('btn-gdrive-restore');
  if (gdriveRestore) gdriveRestore.addEventListener('click', restoreFromDrive);

  const consciousnessBadge = document.getElementById('consciousness-badge');
  if (consciousnessBadge) {
    consciousnessBadge.addEventListener('click', () => { renderConsciousnessPanel(); openModal('modal-consciousness'); });
  }

  document.querySelectorAll('.quick-action').forEach(qa => {
    qa.addEventListener('click', async () => {
      const action = qa.getAttribute('data-action');
      const prompts = {
        code: { ar: 'اكتب لي كود JavaScript يطبع "Hello World"', en: 'Write JavaScript code to print "Hello World"' },
        math: { ar: 'حل المعادلة: 2x + 5 = 15', en: 'Solve: 2x + 5 = 15' },
        translate: { ar: 'ترجم كلمة hello', en: 'Translate hello to all languages' },
        explain: { ar: 'اشرح لي مفهوم الذكاء الاصطناعي', en: 'Explain artificial intelligence' }
      };
      const prompt = prompts[action][state.lang] || prompts[action].en;
      await processMessage(prompt);
    });
  });

  window.addEventListener('online', () => { state.isOnline = true; showDeviceInfo(); });
  window.addEventListener('offline', () => { state.isOnline = false; showDeviceInfo(); });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('service-worker.js').catch(() => {});
  }
}

init();
