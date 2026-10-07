/* LIFE by Dr. Pat patient app — minimal service worker: cache the shell, network-first for the API. */
const SHELL = 'life-portal-v1';
const ASSETS = ['/portal', '/design-system/tokens.css', '/journey/static/journey.css', '/journey/static/journey-shared.js',
  '/timeline/vendor/react.min.js', '/timeline/vendor/react-dom.min.js', '/timeline/vendor/babel.min.js'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(ASSETS)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;                      // never cache patient data
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => { const copy = res.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)).catch(() => {}); return res; })));
});
self.addEventListener('push', (e) => {   // Web Push (VAPID) hook — optional, LINE push is the primary channel
  let data = {}; try { data = e.data.json(); } catch (_) {}
  e.waitUntil(self.registration.showNotification(data.title || 'LIFE by Dr. Pat', { body: data.body || '', icon: '/brand/logo.png', data: { url: data.url || '/portal' } }));
});
self.addEventListener('notificationclick', (e) => { e.notification.close(); e.waitUntil(clients.openWindow(e.notification.data.url || '/portal')); });
