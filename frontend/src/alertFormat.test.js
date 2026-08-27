import { describe, expect, it } from "vitest";
import { alertColor, formatEffect } from "./alertFormat";

describe("formatEffect", () => {
  it("returns a human label for a known effect", () => {
    expect(formatEffect("ELEVATOR_CLOSURE")).toBe("Elevator out");
  });

  it("falls back to a readable guess for an unrecognized effect", () => {
    expect(formatEffect("SOME_NEW_EFFECT")).toBe("some new effect");
  });

  it("falls back to 'Alert' when there is no effect at all", () => {
    expect(formatEffect(null)).toBe("Alert");
  });
});

describe("alertColor", () => {
  it("returns red for a severe alert", () => {
    expect(alertColor(9)).toBe("#c0392b");
  });

  it("returns orange for a moderate alert", () => {
    expect(alertColor(5)).toBe("#e67e22");
  });

  it("returns gray for a minor or missing-severity alert", () => {
    expect(alertColor(1)).toBe("#7f8c8d");
    expect(alertColor(null)).toBe("#7f8c8d");
  });
});
