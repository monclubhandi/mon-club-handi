// Service worker : réseau d'abord (données toujours à jour), copie de secours hors connexion
const CACHE = "paralliance-v7";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Les pages du site, les bibliothèques et la base des clubs : réseau d'abord, sinon dernière copie
  const isPage = url.origin === location.origin;
  const isLib = url.hostname === "cdnjs.cloudflare.com";
  const isData = url.hostname.endsWith(".supabase.co") && url.pathname.startsWith("/rest/v1/clubs");
  if (!isPage && !isLib && !isData) return;
  const key = req;
  e.respondWith(
    fetch(req, { cache: "no-cache" }).then(res => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(key, copy));
      }
      return res;
    }).catch(() => caches.match(key, { ignoreVary: true }).then(r => r || (isPage ? caches.match("./index.html") : Response.error())))
  );
});
