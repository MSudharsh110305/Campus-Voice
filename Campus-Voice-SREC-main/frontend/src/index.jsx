import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

// Ensure app always uses light mode
document.documentElement.classList.remove('dark');
document.documentElement.style.colorScheme = 'light';

// Capture the PWA install prompt as early as possible — fires before any
// component mounts, so we must store it on window for Profile pages to read.
window._deferredInstallPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  window._deferredInstallPrompt = e;
});
window.addEventListener('appinstalled', () => {
  window._deferredInstallPrompt = null;
});

const rootElement = document.getElementById('root');
const root = createRoot(rootElement);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// ─── SERVICE WORKER REGISTRATION ─────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const reg = await navigator.serviceWorker.register('/service-worker.js');

      // Auto-apply SW updates as soon as a new version installs
      reg.addEventListener('updatefound', () => {
        const newWorker = reg.installing;
        if (!newWorker) return;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New SW is waiting — tell it to skip waiting and take control immediately
            newWorker.postMessage({ type: 'SKIP_WAITING' });
          }
        });
      });

      // Listen for PERIODIC_REFRESH messages from the SW
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data?.type === 'PERIODIC_REFRESH') {
          window.dispatchEvent(new CustomEvent('cv:new-notification'));
        }
      });

      // Register periodic background sync (browsers that support it)
      if ('periodicSync' in reg) {
        try {
          const status = await navigator.permissions.query({ name: 'periodic-background-sync' });
          if (status.state === 'granted') {
            await reg.periodicSync.register('cv-refresh-notifications', { minInterval: 5 * 60 * 1000 });
          }
        } catch {
          // periodic sync not supported — polling covers this
        }
      }

      // Set up push notifications if the user is logged in
      setupPushNotifications(reg);
    } catch {
      // SW registration failed silently — app still works without it
    }
  });
}

// ─── PUSH NOTIFICATION SETUP ─────────────────────────────────────────────────

/**
 * Converts a URL-safe base64 VAPID public key to a Uint8Array
 * as required by pushManager.subscribe().
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

async function setupPushNotifications(reg) {
  try {
    // Only run if push and Notification APIs are available
    if (!('Notification' in window) || !('pushManager' in reg) || !('PushManager' in window)) return;

    // Only subscribe if a logged-in user exists
    const userJson = localStorage.getItem('user');
    if (!userJson) return;

    // Only run if VAPID key is configured
    const vapidKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
    if (!vapidKey) return;

    // Request notification permission (no-op if already granted/denied)
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return;

    // Reuse existing subscription if already subscribed
    const existing = await reg.pushManager.getSubscription();
    if (existing) return;

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });

    // Send subscription to backend
    const { tokenStorage } = await import('./utils/api.js');
    const token = tokenStorage.getAccessToken();
    if (!token) return;

    const subJson = sub.toJSON();
    await fetch('/api/notifications/push/subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        endpoint: subJson.endpoint,
        p256dh: subJson.keys?.p256dh,
        auth: subJson.keys?.auth,
      }),
    });
  } catch {
    // Push setup is best-effort — never block the app
  }
}

// Expose so AuthContext can trigger push subscription on login
window._cvSetupPush = async () => {
  const reg = await navigator.serviceWorker.getRegistration();
  if (reg) setupPushNotifications(reg);
};
