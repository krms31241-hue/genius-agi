const INTERNET_CACHE = {};
const LEARNED_TOPICS = new Set();
let isLearning = false;

async function searchWikipedia(query) {
  try {
    const url = 'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + encodeURIComponent(query) + '&format=json&origin=*&srlimit=3';
    const res = await fetch(url, { mode: 'cors' });
    const data = await res.json();
    return data.query ? data.query.search : [];
  } catch (e) { return []; }
}

async function getWikipediaSummary(title) {
  try {
    const url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(title);
    const res = await fetch(url, { mode: 'cors' });
    if (!res.ok) return null;
    const data = await res.json();
    return data.extract ? { title: data.title, extract: data.extract, description: data.description, url: data.content_urls ? data.content_urls.desktop.page : null } : null;
  } catch (e) { return null; }
}

async function autoLearn(query) {
  if (!state.isOnline || isLearning) return null;
  isLearning = true;
  const cleanQuery = query.toLowerCase().replace(/[^a-z0-9\s]/g, '').trim();
  if (LEARNED_TOPICS.has(cleanQuery) || INTERNET_CACHE[cleanQuery]) { isLearning = false; return INTERNET_CACHE[cleanQuery]; }
  let result = await getWikipediaSummary(query);
  if (!result) {
    const searchResults = await searchWikipedia(query);
    if (searchResults.length > 0) result = await getWikipediaSummary(searchResults[0].title);
  }
  if (result) {
    INTERNET_CACHE[cleanQuery] = result;
    LEARNED_TOPICS.add(cleanQuery);
    KNOWLEDGE_BASE.facts[result.title.toLowerCase()] = result.extract;
    state.memory.facts.push({ type: 'internet_learned', topic: result.title, content: result.extract, url: result.url, date: Date.now() });
    if (state.memory.facts.length > 50) state.memory.facts = state.memory.facts.slice(-50);
    await saveMemory();
  }
  isLearning = false;
  return result;
}

async function internetSearchResponse(query) {
  if (!state.isOnline) return null;
  showAutoLearnStatus('Searching internet...');
  const result = await autoLearn(query);
  if (!result) { hideAutoLearnStatus(); return null; }
  hideAutoLearnStatus();
  showAutoLearnStatus('Learned: ' + result.title);
  setTimeout(hideAutoLearnStatus, 3000);
  let response = '**' + result.title + '**\n\n' + result.extract;
  if (result.description) response = '**' + result.title + '** — *' + result.description + '*\n\n' + result.extract;
  if (result.url) response += '\n\n[Read more](' + result.url + ')';
  return response;
}

async function backgroundLearning() {
  if (!state.isOnline || (state.deviceProfile && state.deviceProfile.power === 'low')) return;
  const topics = ['artificial intelligence', 'quantum computing', 'neuroscience', 'space exploration', 'renewable energy', 'biotechnology', 'cybersecurity'];
  const topic = topics[Math.floor(Math.random() * topics.length)];
  if (!LEARNED_TOPICS.has(topic)) { await autoLearn(topic); console.log('[Auto-Learn] ' + topic); }
}

function startBackgroundLearning() {
  if (state.deviceProfile && state.deviceProfile.power === 'low') return;
  setInterval(() => { if (state.isOnline) backgroundLearning(); }, 5 * 60 * 1000);
}

function showAutoLearnStatus(text) {
  const badge = document.getElementById('auto-learn-badge');
  const txt = document.getElementById('auto-learn-text');
  if (badge && txt) { badge.style.display = 'flex'; txt.textContent = text || 'Learning...'; }
}

function hideAutoLearnStatus() {
  const badge = document.getElementById('auto-learn-badge');
  if (badge) badge.style.display = 'none';
}
