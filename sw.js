/* Minimal service worker: lets Chrome offer "Install app". Data always comes live from the laptop. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).catch(() => new Response(
    '<meta name=viewport content="width=device-width,initial-scale=1"><body style="font:18px system-ui;padding:32px;text-align:center"><h2>APIS is not reachable</h2><p>Make sure APIS is running on your laptop and this device is on the same Wi-Fi.</p>',
    {headers: {'Content-Type': 'text/html'}})));
});
