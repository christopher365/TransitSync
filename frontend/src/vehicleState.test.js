import { describe, expect, it } from "vitest";
import { applyVehicleUpdate } from "./vehicleState";

function makePosition(overrides = {}) {
  return {
    vehicle_id: "y1",
    route_id: "Red",
    latitude: 42.35,
    longitude: -71.06,
    current_status: "IN_TRANSIT_TO",
    ...overrides,
  };
}

describe("applyVehicleUpdate", () => {
  it("adds a new vehicle to empty state", () => {
    const result = applyVehicleUpdate({}, makePosition());

    expect(result).toEqual({ y1: makePosition() });
  });

  it("overwrites an existing vehicle with its latest position", () => {
    const initial = { y1: makePosition({ latitude: 42.0 }) };

    const result = applyVehicleUpdate(initial, makePosition({ latitude: 42.5 }));

    expect(result.y1.latitude).toBe(42.5);
  });

  it("leaves other vehicles untouched", () => {
    const initial = { y2: makePosition({ vehicle_id: "y2" }) };

    const result = applyVehicleUpdate(initial, makePosition({ vehicle_id: "y1" }));

    expect(result).toEqual({
      y1: makePosition({ vehicle_id: "y1" }),
      y2: makePosition({ vehicle_id: "y2" }),
    });
  });

  it("does not mutate the original state object", () => {
    const initial = { y2: makePosition({ vehicle_id: "y2" }) };

    applyVehicleUpdate(initial, makePosition({ vehicle_id: "y1" }));

    expect(initial).toEqual({ y2: makePosition({ vehicle_id: "y2" }) });
  });
});
