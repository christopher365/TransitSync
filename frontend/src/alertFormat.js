// MBTA's effect codes are SCREAMING_SNAKE_CASE identifiers, not something
// to show a rider directly. Known ones get a human label; anything new
// MBTA introduces later still degrades gracefully instead of disappearing.
const EFFECT_LABELS = {
  DELAY: "Delay",
  DETOUR: "Detour",
  STOP_CLOSURE: "Stop closed",
  STATION_CLOSURE: "Station closed",
  STOP_MOVED: "Stop moved",
  ELEVATOR_CLOSURE: "Elevator out",
  ESCALATOR_CLOSURE: "Escalator out",
  SERVICE_CHANGE: "Service change",
  SHUTTLE: "Shuttle bus",
  SUSPENSION: "Suspended",
  TRACK_CHANGE: "Track change",
  SNOW_ROUTE: "Snow route",
  CANCELLATION: "Cancelled",
};

export function formatEffect(effect) {
  if (!effect) return "Alert";
  return EFFECT_LABELS[effect] ?? effect.replaceAll("_", " ").toLowerCase();
}

// MBTA's severity is 0 (informational) to 10 (severe). Grouped into three
// bands rather than a 0-10 gradient, since a rider needs "how much should
// I care," not a precise number.
export function alertColor(severity) {
  if (severity == null) return "#7f8c8d";
  if (severity >= 7) return "#c0392b";
  if (severity >= 3) return "#e67e22";
  return "#7f8c8d";
}
