import { describe, expect, it } from "vitest";
import {
  applyVehicleUpdate,
  estimateSpeedMph,
  formatSpeedMph,
  formatUpdatedAgo,
} from "./vehicleState";

function makePosition(overrides = {}) {
  return {
    vehicle_id: "y1",
    route_id: "Red",
    latitude: 42.35,
    longitude: -71.06,
    current_status: "IN_TRANSIT_TO",
    speed: null,
    updated_at: "2026-08-26T22:00:00Z",
    ...overrides,
  };
}

describe("applyVehicleUpdate", () => {
  it("adds a new vehicle to empty state", () => {
    const result = applyVehicleUpdate({}, makePosition());

    // No previous position to compare against yet, so no estimate.
    expect(result).toEqual({ y1: { ...makePosition(), estimatedSpeedMph: null } });
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
      y1: { ...makePosition({ vehicle_id: "y1" }), estimatedSpeedMph: null },
      y2: makePosition({ vehicle_id: "y2" }), // untouched — never passed through applyVehicleUpdate
    });
  });

  it("does not mutate the original state object", () => {
    const initial = { y2: makePosition({ vehicle_id: "y2" }) };

    applyVehicleUpdate(initial, makePosition({ vehicle_id: "y1" }));

    expect(initial).toEqual({ y2: makePosition({ vehicle_id: "y2" }) });
  });

  it("attaches an estimated speed when MBTA doesn't report one and a previous position exists", () => {
    const initial = {
      y1: makePosition({ latitude: 42.36, longitude: -71.06, updated_at: "2026-08-26T22:00:00Z" }),
    };

    const result = applyVehicleUpdate(
      initial,
      makePosition({ latitude: 42.361, longitude: -71.061, updated_at: "2026-08-26T22:00:10Z" }),
    );

    expect(result.y1.estimatedSpeedMph).toBeGreaterThan(0);
  });

  it("does not estimate when MBTA already reports a real speed", () => {
    const initial = { y1: makePosition({ latitude: 42.36, longitude: -71.06 }) };

    const result = applyVehicleUpdate(
      initial,
      makePosition({ latitude: 42.361, longitude: -71.061, speed: 12.5 }),
    );

    expect(result.y1.estimatedSpeedMph).toBeNull();
  });
});

describe("estimateSpeedMph", () => {
  it("returns null when there is no previous position to compare against", () => {
    expect(estimateSpeedMph(null, makePosition())).toBeNull();
  });

  it("returns 0 for two identical positions (a stopped vehicle)", () => {
    const previous = makePosition({ updated_at: "2026-08-26T22:00:00Z" });
    const current = makePosition({ updated_at: "2026-08-26T22:00:10Z" });

    expect(estimateSpeedMph(previous, current)).toBe(0);
  });

  it("returns null when the interval is too short to trust (GPS jitter dominates)", () => {
    const previous = makePosition({
      latitude: 42.36,
      longitude: -71.06,
      updated_at: "2026-08-26T22:00:00Z",
    });
    const current = makePosition({
      latitude: 42.361,
      longitude: -71.061,
      updated_at: "2026-08-26T22:00:01Z", // 1s later — below the trust threshold
    });

    expect(estimateSpeedMph(previous, current)).toBeNull();
  });

  it("returns a plausible positive estimate for a realistic displacement", () => {
    const previous = makePosition({
      latitude: 42.36,
      longitude: -71.06,
      updated_at: "2026-08-26T22:00:00Z",
    });
    const current = makePosition({
      latitude: 42.361,
      longitude: -71.061,
      updated_at: "2026-08-26T22:00:10Z",
    });

    const estimate = estimateSpeedMph(previous, current);

    expect(estimate).toBeGreaterThan(0);
    expect(estimate).toBeLessThan(80); // sanity bound — not a jitter-driven absurd figure
  });

  it("estimates a slower speed for the same distance covered over more time", () => {
    const previous = makePosition({
      latitude: 42.36,
      longitude: -71.06,
      updated_at: "2026-08-26T22:00:00Z",
    });
    const near = makePosition({
      latitude: 42.361,
      longitude: -71.061,
      updated_at: "2026-08-26T22:00:10Z",
    });
    const far = makePosition({
      latitude: 42.361,
      longitude: -71.061,
      updated_at: "2026-08-26T22:01:00Z",
    });

    expect(estimateSpeedMph(previous, near)).toBeGreaterThan(estimateSpeedMph(previous, far));
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
