const CACHE_NAME = 'edu-viewer-v1';
const ASSETS = [
    '/edu-viewer/',
    '/edu-viewer/static/css/bulma.min.css',
    '/edu-viewer/static/js/jquery-3.4.1.min.js',
    '/edu-viewer/static/asset/pwa-icon.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
