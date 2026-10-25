import { describe, it, expect } from "vitest";
import { bearing, fitViewToAspect, greatCircleArc, pointOnArc, screenHeading, viewForPoints } from "../geo";

const BOGOTA = { lat: 4.7016, lon: -74.1469 };
const MEDELLIN = { lat: 6.1645, lon: -75.4231 };

describe("greatCircleArc", () => {
  it("starts and ends exactly at the given airports", () => {
    const arc = greatCircleArc(BOGOTA, MEDELLIN, 32);
    expect(arc.lat).toHaveLength(33);
    expect(arc.lat[0]).toBe(BOGOTA.lat);
    expect(arc.lon[0]).toBe(BOGOTA.lon);
    expect(arc.lat[32]).toBe(MEDELLIN.lat);
    expect(arc.lon[32]).toBe(MEDELLIN.lon);
  });

  it("keeps intermediate points between the endpoints for a short domestic route", () => {
    const arc = greatCircleArc(BOGOTA, MEDELLIN, 16);
    for (let i = 0; i < arc.lat.length; i += 1) {
      expect(arc.lat[i]).toBeGreaterThanOrEqual(BOGOTA.lat - 0.2);
      expect(arc.lat[i]).toBeLessThanOrEqual(MEDELLIN.lat + 0.2);
    }
  });

  it("does not interpolate when both points are the same", () => {
    const arc = greatCircleArc(BOGOTA, BOGOTA);
    expect(arc.lat).toEqual([BOGOTA.lat, BOGOTA.lat]);
  });

  it("avoids a 360 degree jump when crossing the antimeridian", () => {
    const arc = greatCircleArc({ lat: 0, lon: 170 }, { lat: 0, lon: -170 }, 20);
    for (let i = 1; i < arc.lon.length; i += 1) {
      expect(Math.abs(arc.lon[i] - arc.lon[i - 1])).toBeLessThan(180);
    }
  });
});

describe("bearing", () => {
  it("points north, east, south and west on the cardinal cases", () => {
    expect(bearing({ lat: 0, lon: 0 }, { lat: 10, lon: 0 })).toBeCloseTo(0, 5);
    expect(bearing({ lat: 0, lon: 0 }, { lat: 0, lon: 10 })).toBeCloseTo(90, 5);
    expect(bearing({ lat: 0, lon: 0 }, { lat: -10, lon: 0 })).toBeCloseTo(180, 5);
    expect(bearing({ lat: 0, lon: 0 }, { lat: 0, lon: -10 })).toBeCloseTo(270, 5);
  });

  it("gives a north-west heading from Bogota to Medellin", () => {
    const heading = bearing(BOGOTA, MEDELLIN);
    expect(heading).toBeGreaterThan(270);
    expect(heading).toBeLessThan(360);
  });
});

describe("screenHeading", () => {
  it("is measured clockwise from the top of the screen", () => {
    expect(screenHeading({ lat: 0, lon: 0 }, { lat: 5, lon: 0 })).toBeCloseTo(0, 5);
    expect(screenHeading({ lat: 0, lon: 0 }, { lat: 0, lon: 5 })).toBeCloseTo(90, 5);
    expect(screenHeading({ lat: 0, lon: 0 }, { lat: -5, lon: 0 })).toBeCloseTo(180, 5);
    expect(screenHeading({ lat: 0, lon: 0 }, { lat: 0, lon: -5 })).toBeCloseTo(270, 5);
  });

  it("points up-left (north-west) for Bogota to San Andres", () => {
    const heading = screenHeading({ lat: 4.7, lon: -74.1 }, { lat: 12.58, lon: -81.71 });
    expect(heading).toBeGreaterThan(270);
    expect(heading).toBeLessThan(360);
  });
});

describe("pointOnArc", () => {
  it("returns the endpoints at t=0 and t=1 and clamps out-of-range values", () => {
    const arc = greatCircleArc(BOGOTA, MEDELLIN, 10);
    expect(pointOnArc(arc, 0).lat).toBeCloseTo(BOGOTA.lat, 6);
    expect(pointOnArc(arc, 1).lon).toBeCloseTo(MEDELLIN.lon, 6);
    expect(pointOnArc(arc, -3).lat).toBeCloseTo(BOGOTA.lat, 6);
    expect(pointOnArc(arc, 7).lat).toBeCloseTo(MEDELLIN.lat, 6);
  });

  it("returns a heading consistent with the direction of travel", () => {
    const arc = greatCircleArc(BOGOTA, MEDELLIN, 10);
    const mid = pointOnArc(arc, 0.5);
    expect(Math.abs(mid.heading - screenHeading(BOGOTA, MEDELLIN))).toBeLessThan(10);
  });
});

describe("viewForPoints", () => {
  it("returns null without points", () => {
    expect(viewForPoints([])).toBeNull();
  });

  it("contains every point with margin", () => {
    const view = viewForPoints([BOGOTA, MEDELLIN]);
    expect(view).not.toBeNull();
    if (!view) return;
    for (const p of [BOGOTA, MEDELLIN]) {
      expect(p.lat).toBeGreaterThan(view.latRange[0]);
      expect(p.lat).toBeLessThan(view.latRange[1]);
      expect(p.lon).toBeGreaterThan(view.lonRange[0]);
      expect(p.lon).toBeLessThan(view.lonRange[1]);
    }
  });

  it("enforces a minimum span for a single point", () => {
    const view = viewForPoints([BOGOTA], 0, 6);
    expect(view).not.toBeNull();
    if (!view) return;
    expect(view.lonRange[1] - view.lonRange[0]).toBeCloseTo(6, 5);
  });
});

describe("fitViewToAspect", () => {
  const TALL = { lonRange: [-80, -70] as [number, number], latRange: [-5, 15] as [number, number] };

  it("widens a tall view for a wide container without shrinking it", () => {
    const fitted = fitViewToAspect(TALL, 1.6);
    expect(fitted.lonRange[0]).toBeLessThan(TALL.lonRange[0]);
    expect(fitted.lonRange[1]).toBeGreaterThan(TALL.lonRange[1]);
    expect(fitted.latRange).toEqual(TALL.latRange);
  });

  it("extends latitude for a wide view in a tall container", () => {
    const wide = { lonRange: [-90, -60] as [number, number], latRange: [0, 5] as [number, number] };
    const fitted = fitViewToAspect(wide, 0.7);
    expect(fitted.latRange[0]).toBeLessThan(0);
    expect(fitted.latRange[1]).toBeGreaterThan(5);
    expect(fitted.lonRange).toEqual(wide.lonRange);
  });

  it("ignores invalid aspect ratios", () => {
    expect(fitViewToAspect(TALL, 0)).toBe(TALL);
    expect(fitViewToAspect(TALL, Number.NaN)).toBe(TALL);
  });
});
