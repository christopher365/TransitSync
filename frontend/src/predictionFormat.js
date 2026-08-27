// Pulled out as plain functions (no React, no fetch) so the "how do we turn
// a prediction into display text" logic is unit-testable without needing to
// fake a network call or deal with the real system clock.

export function minutesUntil(isoString, now = new Date()) {
  if (!isoString) return null;
  const diffMs = new Date(isoString) - now;
  return Math.max(0, Math.round(diffMs / 60000));
}

export function formatArrival(prediction, now = new Date()) {
  const time = prediction.arrival_time ?? prediction.departure_time;
  if (!time) return prediction.status ?? "Unknown";

  const minutes = minutesUntil(time, now);
  if (minutes === 0) return "Arriving now";
  return `${minutes} min`;
}

// MBTA's own official line colors, so route badges read as authentically
// "MBTA" rather than arbitrary app colors.
const ROUTE_COLORS = {
  Red: "#da291c",
  Mattapan: "#da291c",
  Orange: "#ed8b00",
  Blue: "#003da5",
  "Green-B": "#00843d",
  "Green-C": "#00843d",
  "Green-D": "#00843d",
  "Green-E": "#00843d",
};

export function routeColor(routeId) {
  return ROUTE_COLORS[routeId] ?? "#555555";
}
