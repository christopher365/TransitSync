// Derives the backend's address from whatever host was used to load this
// page, rather than hardcoding "localhost" — the same reasoning as
// useVehicleWebSocket's URL derivation, shared here since REST calls
// (stop search, predictions) need the same address.
export function backendOrigin() {
  const protocol = window.location.protocol === "https:" ? "https" : "http";
  return `${protocol}://${window.location.hostname}:8000`;
}
