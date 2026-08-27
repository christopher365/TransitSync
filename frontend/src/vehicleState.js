// Pulled out as a plain function (no React, no WebSocket) so the actual
// "how do we merge in a new position" logic can be unit tested directly,
// without needing to fake a WebSocket connection just to test it.
export function applyVehicleUpdate(vehiclesById, position) {
  return {
    ...vehiclesById,
    [position.vehicle_id]: position,
  };
}

const METERS_PER_SECOND_TO_MPH = 2.23694;

// MBTA reports speed in meters/second — not a unit anyone reading a popup
// thinks in. null/undefined (a stopped vehicle often has no speed at all)
// stays null rather than rendering "0 mph" or "NaN mph".
export function formatSpeedMph(metersPerSecond) {
  if (metersPerSecond == null) return null;
  return Math.round(metersPerSecond * METERS_PER_SECOND_TO_MPH);
}

// How stale is this specific marker's data — directly relevant after the
// "arriving now but miles away" incident, where not knowing a prediction
// was stale was the actual problem. Seeing "Updated 3s ago" vs "Updated
// 4 min ago" lets a rider judge that for themselves at a glance.
export function formatUpdatedAgo(isoString, now = new Date()) {
  if (!isoString) return "unknown";

  const seconds = Math.max(0, Math.round((now - new Date(isoString)) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.round(seconds / 60);
  return `${minutes} min ago`;
}
