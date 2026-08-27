// Derives the backend's address from whatever host was used to load this
// page, rather than hardcoding "localhost" — correct for local dev and
// docker-compose, where frontend and backend share a host and the backend
// is always on port 8000.
//
// Once frontend and backend are deployed to genuinely different hosts
// (e.g. separate Render services on different domains), that assumption
// breaks — so VITE_API_BASE_URL, when set, overrides it entirely. This is
// the one place that decision is made; both REST calls and the WebSocket
// URL derive from it.
export function backendOrigin() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) return configured.replace(/\/$/, "");

  const protocol = window.location.protocol === "https:" ? "https" : "http";
  return `${protocol}://${window.location.hostname}:8000`;
}
