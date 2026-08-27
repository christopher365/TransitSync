import { describe, expect, it } from "vitest";
import { applyVehicleUpdate, formatSpeedMph, formatUpdatedAgo } from "./vehicleState";

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

describe("formatSpeedMph", () => {
  it("converts meters/second to a rounded mph figure", () => {
    expect(formatSpeedMph(10)).toBe(22); // 10 m/s ≈ 22.4 mph
  });

  it("returns null when speed is missing, rather than 0 or NaN", () => {
    expect(formatSpeedMph(null)).toBeNull();
    expect(formatSpeedMph(undefined)).toBeNull();
  });

  it("handles zero speed (a stopped vehicle) as an actual zero", () => {
    expect(formatSpeedMph(0)).toBe(0);
  });
});

describe("formatUpdatedAgo", () => {
  const now = new Date("2026-08-26T22:00:00Z");

  it("says 'just now' for a very fresh update", () => {
    expect(formatUpdatedAgo("2026-08-26T21:59:58Z", now)).toBe("just now");
  });

  it("shows whole seconds for a recent update", () => {
    expect(formatUpdatedAgo("2026-08-26T21:59:40Z", now)).toBe("20s ago");
  });

  it("shows whole minutes once it's been over a minute", () => {
    expect(formatUpdatedAgo("2026-08-26T21:55:00Z", now)).toBe("5 min ago");
  });

  it("returns 'unknown' when there is no timestamp at all", () => {
    expect(formatUpdatedAgo(null, now)).toBe("unknown");
  });
});
