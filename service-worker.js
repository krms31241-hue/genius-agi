const CACHE_NAME = 'genius-agi-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/css/styles.css',
  '/js/i18n.js',
  '/js/ai-engine.js',
  '/js/consciousness.js',
  '/js/internet.js',
  '/js/gdrive.js',
  '/js/app.js'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(cacheNames => Promise.all(cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name)))));
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(caches.match(event.request).then(response => {
    if (response) return response;
    return fetch(event.request).catch(() => { if (event.request.mode === 'navigate') return caches.match('/offline.html'); });
  }));
});
