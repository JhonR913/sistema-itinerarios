import { describe, it, expect } from "vitest";
import { formatDuration, formatTravelDate, parseIsoDate, todayIso } from "../format";

describe("parseIsoDate", () => {
  it("builds a local date without shifting the day", () => {
    const date = parseIsoDate("2026-10-25");
    expect(date?.getFullYear()).toBe(2026);
    expect(date?.getMonth()).toBe(9);
    expect(date?.getDate()).toBe(25);
  });

  it("returns null for invalid input", () => {
    expect(parseIsoDate("no-es-fecha")).toBeNull();
  });
});

describe("formatTravelDate", () => {
  it("falls back to the raw value when the date is invalid", () => {
    expect(formatTravelDate("xx")).toBe("xx");
  });

  it("includes the year and day for a valid date", () => {
    const text = formatTravelDate("2026-10-25");
    expect(text).toContain("2026");
    expect(text).toContain("25");
  });
});

describe("formatDuration", () => {
  it("formats minutes, hours and mixed values", () => {
    expect(formatDuration(45)).toBe("45 min");
    expect(formatDuration(120)).toBe("2 h");
    expect(formatDuration(90)).toBe("1 h 30 min");
  });

  it("returns a dash for invalid values", () => {
    expect(formatDuration(-1)).toBe("—");
    expect(formatDuration(Number.NaN)).toBe("—");
  });
});

describe("todayIso", () => {
  it("pads month and day", () => {
    expect(todayIso(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
