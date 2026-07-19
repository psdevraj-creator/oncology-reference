const CACHE_NAME = 'oncology-handbook-v1';

const PRECACHE_URLS = [
  '/',
  '/assets/clientside.js',
];

// Install: cache app shell
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

// Activate: clean old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(name) {
          return name !== CACHE_NAME;
        }).map(function(name) {
          return caches.delete(name);
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch: network-first for pages, cache-first for assets
self.addEventListener('fetch', function(event) {
  var request = event.request;

  // HTML pages: network first, fallback to cache
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(function(response) {
        return caches.open(CACHE_NAME).then(function(cache) {
          cache.put(request, response.clone());
          return response;
        });
      }).catch(function() {
        return caches.match(request);
      })
    );
    return;
  }

  // Static assets (JS, CSS): cache first, update in background
  if (request.url.match(/\.(js|css|png|jpg|svg|woff2?)$/)) {
    event.respondWith(
      caches.match(request).then(function(cached) {
        var fetchPromise = fetch(request).then(function(response) {
          return caches.open(CACHE_NAME).then(function(cache) {
            cache.put(request, response.clone());
            return response;
          });
        });
        return cached || fetchPromise;
      })
    );
    return;
  }

  // Everything else: network only
  event.respondWith(fetch(request));
});
