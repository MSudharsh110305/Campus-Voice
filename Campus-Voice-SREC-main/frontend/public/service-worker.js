const CACHE_STATIC = 'cv-static-v3';
const CACHE_API = 'cv-api-v3';
const STATIC_ASSETS = ['/', '/offline.html', '/manifest.webmanifest'];

// --- INSTALL ---
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_STATIC).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// --- ACTIVATE ---
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_STATIC && k !== CACHE_API)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// --- FETCH ---
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== location.origin) return;

  // Skip non-GET for API (let them through)
  if (url.pathname.startsWith('/api/') && request.method !== 'GET') return;

  // Skip auth endpoints entirely
  if (
    url.pathname.includes('/api/auth/') ||
    url.pathname.includes('/students/login') ||
    url.pathname.includes('/authorities/login')
  ) {
    return;
  }

  // API GETs: stale-while-revalidate (skip authenticated requests to avoid 401 replays)
  if (url.pathname.startsWith('/api/') && request.method === 'GET') {
    // Never cache requests with Authorization headers — the api() interceptor handles
    // token refresh transparently; caching would replay stale tokens in the background.
    if (request.headers.get('Authorization')) return;

    event.respondWith(
      caches.open(CACHE_API).then(async (cache) => {
        const cached = await cache.match(request);
        const fetchPromise = fetch(request)
          .then((res) => {
            if (res.ok) cache.put(request, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // Static assets: cache-first
  if (
    /\.(js|css|woff2?|ttf|eot|svg|png|jpg|jpeg|gif|ico|webp)(\?.*)?$/.test(url.pathname)
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((res) => {
            if (res.ok) {
              caches.open(CACHE_STATIC).then((c) => c.put(request, res.clone()));
            }
            return res;
          })
      )
    );
    return;
  }

  // HTML navigation: network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/').then((cached) => cached || caches.match('/offline.html'))
      )
    );
    return;
  }
});

// --- BACKGROUND SYNC (offline complaint queue) ---
self.addEventListener('sync', (event) => {
  if (event.tag === 'submit-complaint') {
    event.waitUntil(submitPendingComplaints());
  }
});

async function submitPendingComplaints() {
  const pending = await getFromIDB();
  for (const item of pending) {
    try {
      const fd = new FormData();
      fd.append('original_text', item.original_text);
      fd.append('visibility', item.visibility || 'Public');
      fd.append('is_anonymous', 'true');
      const res = await fetch('/api/complaints/submit', {
        method: 'POST',
        headers: { Authorization: `Bearer ${item.access_token}` },
        body: fd,
      });
      if (res.ok) await deleteFromIDB(item.id);
    } catch (e) {
      throw e; // let SW retry
    }
  }
}

// --- PERIODIC SYNC (background notification refresh) ---
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'cv-refresh-notifications') {
    event.waitUntil(notifyClientsToRefresh());
  }
});

async function notifyClientsToRefresh() {
  const clientList = await clients.matchAll({ type: 'window', includeUncontrolled: true });
  for (const client of clientList) {
    client.postMessage({ type: 'PERIODIC_REFRESH' });
  }
}

// Minimal IndexedDB helpers inside SW
function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('cv-offline-db', 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pending-complaints')) {
        db.createObjectStore('pending-complaints', { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}
async function getFromIDB() {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-complaints', 'readonly');
    const req = tx.objectStore('pending-complaints').getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function deleteFromIDB(id) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pending-complaints', 'readwrite');
    const req = tx.objectStore('pending-complaints').delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// --- PUSH NOTIFICATIONS ---
self.addEventListener('push', (event) => {
  let data = { title: 'CampusVoice', body: 'You have a new notification', url: '/', urgency: 'normal' };
  try { data = { ...data, ...event.data.json() }; } catch (e) {}

  const showAndNotify = self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/icons/icon-192.svg',
    badge: '/icons/icon-192.svg',
    data: { url: data.url },
    // Vibration is in SW (not React) — works even when app is closed
    vibrate: data.urgency === 'high' ? [200, 100, 200, 100, 200] : [150, 50, 150],
    tag: data.type || 'cv-notification',
    renotify: true,
    requireInteraction: data.urgency === 'high',
  }).then(() => {
    // Tell any open tabs to refresh their notification counts immediately
    if ('BroadcastChannel' in self) {
      const bc = new BroadcastChannel('cv-notifications');
      bc.postMessage({ type: 'PUSH_RECEIVED', data });
      bc.close();
    }
  });

  event.waitUntil(showAndNotify);
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.registration.scope) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// --- SW UPDATE & MESSAGES ---
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
