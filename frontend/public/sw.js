/* Cloud AI Trader X Pro — service worker.
 * Security-first: NEVER caches API responses, WebSocket traffic, or anything
 * carrying market data / tokens. Only the static app shell is cached so the
 * UI loads instantly and offline shows a graceful shell.
 */
const CACHE = "cat-shell-v1";
const SHELL = ["/", "/manifest.webmanifest", "/icons/icon.svg", "/offline.html"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  if (request.method !== "GET") return;                 // never touch writes
  const url = new URL(request.url);

  // Bypass everything sensitive/live — straight to network, no caching.
  if (url.pathname.startsWith("/api") || url.protocol === "ws:" ||
      url.protocol === "wss:" || url.pathname === "/ws") {
    return;
  }

  // Cross-origin (e.g. hosted backend, fonts) — let the browser handle it.
  if (url.origin !== self.location.origin) return;

  // App shell + static assets: cache-first, refresh in background.
  e.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => cached || caches.match("/offline.html"));
      return cached || network;
    })
  );
});

// Web Push (mobile/desktop alerts). Payload is non-sensitive (title/body only).
self.addEventListener("push", (e) => {
  let data = { title: "Cloud AI Trader", body: "New market alert" };
  try { data = e.data ? e.data.json() : data; } catch (_) {}
  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      tag: data.tag || "cat-alert",
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data?.url || "/"));
});
