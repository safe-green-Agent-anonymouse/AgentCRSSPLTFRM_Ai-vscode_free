const CACHE = "nova-studio-v2";
const FILES = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg", "./free-models.js"];
const featureScript = '<script src="./free-models.js"></script>';

async function injectFreeModels(response) {
  if (!response || !response.headers.get("content-type")?.includes("text/html")) return response;
  const html = await response.text();
  if (html.includes("free-models.js")) return new Response(html, response);
  return new Response(html.replace("</body>", `${featureScript}</body>`), {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers
  });
}

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) return;
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).then((response) => {
      if (response.ok) caches.open(CACHE).then((cache) => cache.put("./index.html", response.clone()));
      return injectFreeModels(response);
    }).catch(() => caches.match("./index.html").then(injectFreeModels)));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
    if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
    return response;
  })));
});
