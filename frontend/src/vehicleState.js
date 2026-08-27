// A poll cycle can land close enough together that GPS noise alone would
// dominate the distance measurement, producing a wildly wrong speed
// estimate from what's actually just jitter. Below this interval, don't
// even attempt an estimate — our own poll cadence is ~5s, so anything this
// close together isn't a real, independent second reading anyway.
const MIN_INTERVAL_SECONDS_FOR_ESTIMATE = 3;
const EARTH_RADIUS_MILES = 3958.8;

function toRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

// Great-circle (haversine) distance — accurate enough for the short
// consecutive-report distances involved here; the straight-line vs.
// actual-road-path difference is negligible at this scale.
function haversineDistanceMiles(lat1, lon1, lat2, lon2) {
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_MILES * c;
}

// Estimates a vehicle's speed from two consecutive position reports, for
// when MBTA doesn't supply one itself (common for generic/shuttle
// vehicles). Deliberately only used as a fallback — MBTA's own reported
// speed, when present, reflects the actual road path and instrumentation,
// which this straight-line/two-point estimate can't match.
export function estimateSpeedMph(previous, current) {
  if (!previous || !current) return null;

  const seconds = (new Date(current.updated_at) - new Date(previous.updated_at)) / 1000;
  if (seconds < MIN_INTERVAL_SECONDS_FOR_ESTIMATE) return null;

  const miles = haversineDistanceMiles(
    previous.latitude,
    previous.longitude,
    current.latitude,
    current.longitude,
  );
  return Math.round(miles / (seconds / 3600));
}

// Pulled out as a plain function (no React, no WebSocket) so the actual
// "how do we merge in a new position" logic can be unit tested directly,
// without needing to fake a WebSocket connection just to test it.
export function applyVehicleUpdate(vehiclesById, position) {
  const previous = vehiclesById[position.vehicle_id];
  const estimatedSpeedMph = position.speed == null ? estimateSpeedMph(previous, position) : null;

  return {
    ...vehiclesById,
    [position.vehicle_id]: { ...position, estimatedSpeedMph },
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
