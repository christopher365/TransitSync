import { describe, expect, it } from "vitest";
import {
  distinctRouteIds,
  formatArrival,
  isStalePrediction,
  minutesUntil,
  routeColor,
} from "./predictionFormat";

describe("minutesUntil", () => {
  it("returns null when there is no time", () => {
    expect(minutesUntil(null)).toBeNull();
  });

  it("rounds to the nearest minute", () => {
    const now = new Date("2026-08-26T22:00:00Z");
    const arrival = "2026-08-26T22:03:20Z";

    expect(minutesUntil(arrival, now)).toBe(3);
  });

  it("never returns negative minutes for a time in the past", () => {
    const now = new Date("2026-08-26T22:00:00Z");
    const arrival = "2026-08-26T21:55:00Z";

    expect(minutesUntil(arrival, now)).toBe(0);
  });
});

describe("formatArrival", () => {
  const now = new Date("2026-08-26T22:00:00Z");

  it("prefers arrival_time over departure_time", () => {
    const prediction = {
      arrival_time: "2026-08-26T22:05:00Z",
      departure_time: "2026-08-26T22:06:00Z",
    };

    expect(formatArrival(prediction, now)).toBe("5 min");
  });

  it("falls back to departure_time when arrival_time is missing", () => {
    const prediction = { arrival_time: null, departure_time: "2026-08-26T22:10:00Z" };

    expect(formatArrival(prediction, now)).toBe("10 min");
  });

  it("shows 'Arriving now' for zero minutes", () => {
    const prediction = { arrival_time: "2026-08-26T22:00:10Z", departure_time: null };

    expect(formatArrival(prediction, now)).toBe("Arriving now");
  });

  it("falls back to status text when there is no time at all", () => {
    const prediction = { arrival_time: null, departure_time: null, status: "Stopped 3 stops away" };

    expect(formatArrival(prediction, now)).toBe("Stopped 3 stops away");
  });

  it("falls back to 'Unknown' when there is neither a time nor a status", () => {
    const prediction = { arrival_time: null, departure_time: null, status: null };

    expect(formatArrival(prediction, now)).toBe("Unknown");
  });
});

describe("isStalePrediction", () => {
  const now = new Date("2026-08-26T22:00:00Z");

  it("is not stale when the arrival time is in the future", () => {
    const prediction = { arrival_time: "2026-08-26T22:05:00Z", departure_time: null };

    expect(isStalePrediction(prediction, now)).toBe(false);
  });

  it("is not stale within the grace window just after the arrival time", () => {
    const prediction = { arrival_time: "2026-08-26T21:59:30Z", departure_time: null };

    expect(isStalePrediction(prediction, now)).toBe(false);
  });

  it("is stale well past the arrival time (the bug this guards against)", () => {
    // This is the exact failure mode reported live: a badly-delayed
    // vehicle's prediction was 20 minutes in the past, and the old
    // Math.max(0, ...) clamp in minutesUntil turned that into "0 min" —
    // displayed as "Arriving now" despite the vehicle being miles away.
    const prediction = { arrival_time: "2026-08-26T21:40:00Z", departure_time: null };

    expect(isStalePrediction(prediction, now)).toBe(true);
  });

  it("is never stale when there is no time at all", () => {
    const prediction = { arrival_time: null, departure_time: null, status: "Delayed" };

    expect(isStalePrediction(prediction, now)).toBe(false);
  });
});

describe("routeColor", () => {
  it("returns MBTA's official color for a known route", () => {
    expect(routeColor("Red")).toBe("#da291c");
  });

  it("returns a neutral fallback for an unknown route", () => {
    expect(routeColor("some-future-route")).toBe("#555555");
  });
});

describe("distinctRouteIds", () => {
  it("returns the unique set of route ids across predictions", () => {
    const predictions = [{ route_id: "Red" }, { route_id: "Green-D" }, { route_id: "Red" }];

    expect(distinctRouteIds(predictions)).toEqual(new Set(["Red", "Green-D"]));
  });

  it("ignores predictions with a missing route id", () => {
    const predictions = [{ route_id: "Red" }, { route_id: null }];

    expect(distinctRouteIds(predictions)).toEqual(new Set(["Red"]));
  });

  it("returns an empty set for no predictions", () => {
    expect(distinctRouteIds([])).toEqual(new Set());
  });
});
