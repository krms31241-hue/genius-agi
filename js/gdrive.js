const GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';
const DRIVE_FILE_NAME = 'genius-agi-backup.json';
let googleAccessToken = null;

function loadGoogleScript() {
  return new Promise((resolve, reject) => {
    if (document.getElementById('google-api-script')) { resolve(); return; }
    const script = document.createElement('script');
    script.id = 'google-api-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

async function initGoogleDrive() {
  if (GOOGLE_CLIENT_ID.includes('YOUR_')) { console.log('[GDrive] Not configured'); return; }
  try { await loadGoogleScript(); } catch (e) { console.error('[GDrive]', e); }
}

function signInGoogle() {
  if (GOOGLE_CLIENT_ID.includes('YOUR_')) { toast('Configure Google Client ID in Settings', 'error'); return; }
  const client = google.accounts.oauth2.initTokenClient({
    client_id: GOOGLE_CLIENT_ID,
    scope: 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/drive.appdata',
    callback: (tokenResponse) => {
      if (tokenResponse && tokenResponse.access_token) {
        googleAccessToken = tokenResponse.access_token;
        updateGDriveUI(true);
        toast('Connected to Google Drive', 'success');
      }
    }
  });
  client.requestAccessToken();
}

function signOutGoogle() {
  if (googleAccessToken) {
    google.accounts.oauth2.revoke(googleAccessToken, () => {
      googleAccessToken = null;
      updateGDriveUI(false);
      toast('Signed out', 'info');
    });
  }
}

function updateGDriveUI(connected) {
  const statusEl = document.getElementById('gdrive-status');
  const signinBtn = document.getElementById('btn-gdrive-signin');
  const backupBtn = document.getElementById('btn-gdrive-backup');
  const restoreBtn = document.getElementById('btn-gdrive-restore');
  if (connected) {
    if (statusEl) statusEl.innerHTML = '<span style="color:var(--success)">Connected</span>';
    if (signinBtn) { signinBtn.innerHTML = '<span>🔒</span> <span>Disconnect</span>'; signinBtn.onclick = signOutGoogle; }
    if (backupBtn) backupBtn.style.display = 'flex';
    if (restoreBtn) restoreBtn.style.display = 'flex';
  } else {
    if (statusEl) statusEl.textContent = 'Not connected';
    if (signinBtn) { signinBtn.innerHTML = '<span>🔐</span> <span>Sign in with Google</span>'; signinBtn.onclick = signInGoogle; }
    if (backupBtn) backupBtn.style.display = 'none';
    if (restoreBtn) restoreBtn.style.display = 'none';
  }
}

async function backupToDrive() {
  if (!googleAccessToken) { toast('Sign in first', 'error'); return; }
  try {
    showAutoLearnStatus('Backing up...');
    const data = { chats: state.chats, memory: state.memory, files: state.files, exportDate: Date.now() };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const searchRes = await fetch('https://www.googleapis.com/drive/v3/files?q=name=\'' + DRIVE_FILE_NAME + '\'&spaces=appDataFolder', { headers: { 'Authorization': 'Bearer ' + googleAccessToken } });
    const searchData = await searchRes.json();
    const metadata = { name: DRIVE_FILE_NAME, mimeType: 'application/json', parents: searchData.files && searchData.files.length > 0 ? undefined : ['appDataFolder'] };
    const form = new FormData();
    form.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));
    form.append('file', blob);
    let url = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart';
    let method = 'POST';
    if (searchData.files && searchData.files.length > 0) { url = 'https://www.googleapis.com/upload/drive/v3/files/' + searchData.files[0].id + '?uploadType=multipart'; method = 'PATCH'; }
    const uploadRes = await fetch(url, { method: method, headers: { 'Authorization': 'Bearer ' + googleAccessToken }, body: form });
    hideAutoLearnStatus();
    toast(uploadRes.ok ? 'Backup saved!' : 'Backup failed', uploadRes.ok ? 'success' : 'error');
  } catch (e) { hideAutoLearnStatus(); toast('Backup error: ' + e.message, 'error'); }
}

async function restoreFromDrive() {
  if (!googleAccessToken) { toast('Sign in first', 'error'); return; }
  try {
    showAutoLearnStatus('Restoring...');
    const searchRes = await fetch('https://www.googleapis.com/drive/v3/files?q=name=\'' + DRIVE_FILE_NAME + '\'&spaces=appDataFolder', { headers: { 'Authorization': 'Bearer ' + googleAccessToken } });
    const searchData = await searchRes.json();
    if (!searchData.files || searchData.files.length === 0) { hideAutoLearnStatus(); toast('No backup found', 'error'); return; }
    const downloadRes = await fetch('https://www.googleapis.com/drive/v3/files/' + searchData.files[0].id + '?alt=media', { headers: { 'Authorization': 'Bearer ' + googleAccessToken } });
    const data = JSON.parse(await downloadRes.text());
    if (data.chats) { state.chats = data.chats; state.currentChatId = state.chats[0] ? state.chats[0].id : null; for (const chat of state.chats) await saveChat(chat); }
    if (data.memory) { state.memory = data.memory; await saveMemory(); }
    if (data.files) state.files = data.files;
    renderChatList(); renderMessages();
    hideAutoLearnStatus();
    toast('Restored from Drive!', 'success');
  } catch (e) { hideAutoLearnStatus(); toast('Restore error: ' + e.message, 'error'); }
}

async function checkAndAutoBackup() {
  if (!googleAccessToken || !state.isOnline) return;
  try {
    const usage = await getStorageUsage();
    const sizeMB = parseFloat(usage);
    if (sizeMB > 5) { console.log('[Auto-Backup] Storage high: ' + usage); await backupToDrive(); }
  } catch (e) { console.error('[Auto-Backup]', e); }
}

function startAutoBackup() {
  setInterval(() => { if (state.isOnline && googleAccessToken) checkAndAutoBackup(); }, 10 * 60 * 1000);
}
