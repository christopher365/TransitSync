// Pulled out as a plain function (no React, no WebSocket) so the actual
// "how do we merge in a new position" logic can be unit tested directly,
// without needing to fake a WebSocket connection just to test it.
export function applyVehicleUpdate(vehiclesById, position) {
  return {
    ...vehiclesById,
    [position.vehicle_id]: position,
  };
}
