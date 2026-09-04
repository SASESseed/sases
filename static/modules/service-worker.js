const CACHE_NAME = 'sases-cache-v8';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/favicon.svg',
  '/static/modules/main.js',
  '/static/modules/api.js',
  '/static/modules/auth.js',
  '/static/modules/messages.js',
  '/static/modules/chat.js',
  '/static/modules/group_chat.js',
  '/static/modules/contacts.js',
  '/static/modules/discover.js',
  '/static/modules/me.js',
  '/static/modules/utils.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 忽略非 http/https 请求（如 chrome-extension）
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  // 对于 HTML 或 API 请求，始终使用网络，不缓存，并强制 text/html
  if (url.pathname === '/static/index.html' || url.pathname === '/' ||
      url.pathname.startsWith('/token') || url.pathname.startsWith('/agent') ||
      url.pathname.startsWith('/messages') || url.pathname.startsWith('/models') ||
      url.pathname.startsWith('/credits') || url.pathname.startsWith('/knowledge') ||
      url.pathname.startsWith('/stats') || url.pathname.startsWith('/auth') ||
      url.pathname.startsWith('/api') || url.pathname.startsWith('/seeds') ||
      url.pathname.startsWith('/search') || url.pathname.startsWith('/group') ||
      url.pathname.startsWith('/market') || url.pathname.startsWith('/ai-circle') ||
      url.pathname.startsWith('/wisdom-space') || url.pathname.startsWith('/export')) {
    event.respondWith(
      fetch(event.request).then(response => {
        // 如果是 HTML 请求，确保 Content-Type 正确
        if (url.pathname === '/static/index.html' || url.pathname === '/') {
          const newHeaders = new Headers(response.headers);
          newHeaders.set('Content-Type', 'text/html');
          return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: newHeaders
          });
        }
        return response;
      })
    );
    return;
  }

  // 静态资源缓存优先
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});