import { describe, it, expect } from "vitest";
import { TRACE, buildFigure, colombiaView } from "../figure";
import { buildRoutes } from "../routes";
import type { Airport } from "../../../types/airport";
import type { Itinerary } from "../../../types/itinerary";

const AIRPORTS: Airport[] = [
  { id: "bog", iata_code: "BOG", name: "El Dorado", city: "Bogotá", latitude: 4.7, longitude: -74.15 },
  { id: "mde", iata_code: "MDE", name: "José María Córdova", city: "Rionegro", latitude: 6.16, longitude: -75.42 },
  { id: "adz", iata_code: "ADZ", name: "Gustavo Rojas Pinilla", city: "San Andrés", latitude: 12.58, longitude: -81.71 },
];

const snap = (a: Airport) => ({ airport_id: a.id, iata_code: a.iata_code, name: a.name, city: a.city });
const itinerary = (id: string, from: Airport, to: Airport): Itinerary => ({
  id,
  nombre_usuario: "jhon",
  origin: snap(from),
  destination: snap(to),
  travel_date: "2026-11-01",
  duration_minutes: 60,
});

type Trace = { lat: Array<number | null>; lon: Array<number | null> };
const trace = (figure: ReturnType<typeof buildFigure>, index: number) => figure.data[index] as unknown as Trace;

describe("buildFigure", () => {
  it("passes latitude to `lat` and longitude to `lon` in the airports trace", () => {
    const figure = buildFigure({ airports: AIRPORTS, routes: [], selectedId: null });
    const airports = trace(figure, TRACE.airports);
    expect(airports.lat).toEqual([4.7, 6.16, 12.58]);
    expect(airports.lon).toEqual([-74.15, -75.42, -81.71]);
  });

  it("starts route arcs at the origin and ends them at the destination", () => {
    const { routes } = buildRoutes([itinerary("a", AIRPORTS[0], AIRPORTS[1])], AIRPORTS);
    const figure = buildFigure({ airports: AIRPORTS, routes, selectedId: null });
    const lines = trace(figure, TRACE.routes);
    expect(lines.lat[0]).toBe(4.7);
    expect(lines.lon[0]).toBe(-74.15);
    const lastIndex = lines.lat.length - 2; // el último elemento es el separador null
    expect(lines.lat[lastIndex]).toBe(6.16);
    expect(lines.lon[lastIndex]).toBe(-75.42);
  });

  it("keeps the selected route out of the secondary trace and in the active one", () => {
    const { routes } = buildRoutes([itinerary("a", AIRPORTS[0], AIRPORTS[1])], AIRPORTS);
    const figure = buildFigure({ airports: AIRPORTS, routes, selectedId: "a" });
    expect(trace(figure, TRACE.routes).lat).toEqual([]);
    expect(trace(figure, TRACE.selected).lat.length).toBeGreaterThan(2);
    expect(trace(figure, TRACE.endpoints).lat).toEqual([4.7, 6.16]);
  });

  it("always has the same number of traces, in the order of TRACE", () => {
    const empty = buildFigure({ airports: AIRPORTS, routes: [], selectedId: null });
    expect(empty.data).toHaveLength(Object.keys(TRACE).length);
  });

  it("uses the Colombia view as overview regardless of foreign airports", () => {
    const withForeign: Airport[] = [
      ...AIRPORTS,
      { id: "syd", iata_code: "SYD", name: "Sydney", city: "Sydney", latitude: -33.94, longitude: 151.18 },
    ];
    const a = buildFigure({ airports: AIRPORTS, routes: [], selectedId: null, aspect: 1.5 });
    const b = buildFigure({ airports: withForeign, routes: [], selectedId: null, aspect: 1.5 });
    expect(b.overview).toEqual(a.overview);
  });
});

describe("camera framing", () => {
  const geoRange = (figure: ReturnType<typeof buildFigure>) => {
    const geo = figure.layout.geo as unknown as { lonaxis: { range: number[] }; lataxis: { range: number[] } };
    return { lon: geo.lonaxis.range, lat: geo.lataxis.range };
  };

  it("zooms into the selected route and keeps the Colombia view otherwise", () => {
    const { routes } = buildRoutes([itinerary("a", AIRPORTS[0], AIRPORTS[1])], AIRPORTS);
    const general = geoRange(buildFigure({ airports: AIRPORTS, routes, selectedId: null }));
    const selected = geoRange(buildFigure({ airports: AIRPORTS, routes, selectedId: "a" }));
    expect(selected.lat[1] - selected.lat[0]).toBeLessThan(general.lat[1] - general.lat[0]);
  });

  it("changes uirevision only when the selection, reset key or aspect change", () => {
    const { routes } = buildRoutes([itinerary("a", AIRPORTS[0], AIRPORTS[1])], AIRPORTS);
    const rev = (selectedId: string | null, viewKey = "0", aspect = 1.5) =>
      buildFigure({ airports: AIRPORTS, routes, selectedId, viewKey, aspect }).layout.uirevision;
    expect(rev(null)).toBe(rev(null));
    expect(rev(null)).not.toBe(rev("a"));
    expect(rev(null, "0")).not.toBe(rev(null, "1"));
    expect(rev(null, "0", 1.5)).not.toBe(rev(null, "0", 1.6));
  });
});

describe("colombiaView", () => {
  it("contains continental Colombia and the San Andrés archipelago", () => {
    for (const aspect of [0.7, 1, 1.5, 2.2]) {
      const view = colombiaView(aspect);
      expect(view.lonRange[0]).toBeLessThanOrEqual(-82);
      expect(view.lonRange[1]).toBeGreaterThanOrEqual(-66);
      expect(view.latRange[0]).toBeLessThanOrEqual(-5);
      expect(view.latRange[1]).toBeGreaterThanOrEqual(13.5);
    }
  });

  it("is centred on Colombia, nowhere near a pole or the world", () => {
    const view = colombiaView(1.5);
    const lonCenter = (view.lonRange[0] + view.lonRange[1]) / 2;
    const latCenter = (view.latRange[0] + view.latRange[1]) / 2;
    expect(lonCenter).toBeGreaterThan(-78);
    expect(lonCenter).toBeLessThan(-70);
    expect(latCenter).toBeGreaterThan(2);
    expect(latCenter).toBeLessThan(8);
    expect(view.lonRange[1] - view.lonRange[0]).toBeLessThan(60);
  });
});
