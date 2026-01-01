const CACHE = "lordos-cache-v2";
const ASSETS = [
  "./",
  "./index.html",
  "./css/mobile.css",
  "./js/mobile.js",
  "./manifest.json"
];

// استراتيجية التخزين المؤقت المحسّنة
const CACHE_STRATEGIES = {
  assets: "cache-first",
  api: "network-first"
};

self.addEventListener("install", e => {
  console.log("Service Worker: Installing...");
  e.waitUntil(
    caches.open(CACHE).then(c => {
      console.log("Service Worker: Caching assets");
      return c.addAll(ASSETS);
    })
  );
  self.skipWaiting(); // تفعيل الـ Service Worker الجديد فوراً
});

self.addEventListener("activate", e => {
  console.log("Service Worker: Activating...");
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE)
          .map(k => {
            console.log("Service Worker: Removing old cache", k);
            return caches.delete(k);
          })
      )
    )
  );
  self.clients.claim(); // السيطرة على جميع الصفحات المفتوحة
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  
  // استثناء طلبات API من التخزين المؤقت
  if (e.request.url.includes("/api/") || e.request.url.includes("openrouter.ai")) {
    e.respondWith(fetch(e.request));
    return;
  }
  
  // استراتيجية cache-first للأصول المحلية
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) {
        console.log("Service Worker: Serving from cache", e.request.url);
        return cached;
      }
      
      return fetch(e.request).then(response => {
        // تخزين الاستجابات الناجحة
        if (response && response.status === 200) {
          return caches.open(CACHE).then(cache => {
            cache.put(e.request, response.clone());
            return response;
          });
        }
        return response;
      }).catch(err => {
        console.error("Service Worker: Fetch failed", err);
        throw err;
      });
    })
  );
});
