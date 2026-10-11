const CACHE = "nova-studio-v3";
const FILES = ["./", "./index.html", "./manifest.webmanifest", "./icon.svg", "./free-models.js", "./messages-ui.js"];
const UI_SCRIPTS = ["messages-ui.js", "free-models.js"];

async function injectUiScripts(response) {
  if (!response || !response.headers.get("content-type")?.includes("text/html")) return response;
  let html = await response.text();
  for (const script of UI_SCRIPTS) {
    if (!html.includes(script)) html = html.replace("</body>", `<script src="./${script}"></script></body>`);
  }
  const headers = new Headers(response.headers);
  headers.delete("content-length");
  headers.delete("content-encoding");
  headers.delete("transfer-encoding");
  return new Response(html, { status: response.status, statusText: response.statusText, headers });
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
      return injectUiScripts(response);
    }).catch(() => caches.match("./index.html").then(injectUiScripts)));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
    if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
    return response;
  })));
});
