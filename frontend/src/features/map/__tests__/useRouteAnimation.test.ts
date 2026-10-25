import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";

const restyle = vi.fn(() => Promise.resolve());
vi.mock("../plotly", () => ({ Plotly: { restyle: (...args: unknown[]) => (restyle as (...a: unknown[]) => Promise<void>)(...args) } }));

import { useRouteAnimation } from "../useRouteAnimation";
import { buildRoutes } from "../routes";

const BOG = { id: "bog", iata_code: "BOG", name: "El Dorado", city: "Bogotá", latitude: 4.7, longitude: -74.15 };
const MDE = { id: "mde", iata_code: "MDE", name: "JMC", city: "Rionegro", latitude: 6.16, longitude: -75.42 };
const snap = (a: typeof BOG) => ({ airport_id: a.id, iata_code: a.iata_code, name: a.name, city: a.city });

const { routes } = buildRoutes(
  [
    {
      id: "i1",
      nombre_usuario: "jhon",
      origin: snap(BOG),
      destination: snap(MDE),
      travel_date: "2026-11-01",
      duration_minutes: 60,
    },
  ],
  [BOG, MDE],
);

describe("useRouteAnimation", () => {
  let frames: Map<number, FrameRequestCallback>;
  let nextId: number;

  beforeEach(() => {
    restyle.mockClear();
    frames = new Map();
    nextId = 1;
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      frames.set(nextId, cb);
      return nextId++;
    });
    vi.stubGlobal("cancelAnimationFrame", (id: number) => frames.delete(id));
  });

  afterEach(() => vi.unstubAllGlobals());

  const graph = () => ({ current: document.createElement("div") });

  it("schedules frames while enabled and cancels them on unmount", () => {
    const { unmount } = renderHook(() => useRouteAnimation(graph(), routes[0], true));
    expect(frames.size).toBe(1);
    unmount();
    expect(frames.size).toBe(0);
  });

  it("does not animate when disabled, but places the plane once at rest", () => {
    renderHook(() => useRouteAnimation(graph(), routes[0], false));
    expect(frames.size).toBe(0);
    expect(restyle).toHaveBeenCalledTimes(1);
  });

  it("does nothing without a selected route", () => {
    renderHook(() => useRouteAnimation(graph(), null, true));
    expect(frames.size).toBe(0);
    expect(restyle).not.toHaveBeenCalled();
  });

  it("stops the previous loop when the selection changes", () => {
    const ref = graph();
    const { rerender } = renderHook(({ route }) => useRouteAnimation(ref, route, true), {
      initialProps: { route: routes[0] as (typeof routes)[number] | null },
    });
    expect(frames.size).toBe(1);
    rerender({ route: null });
    expect(frames.size).toBe(0);
  });

  it("removes the visibilitychange listener on unmount", () => {
    const remove = vi.spyOn(document, "removeEventListener");
    const { unmount } = renderHook(() => useRouteAnimation(graph(), routes[0], true));
    unmount();
    expect(remove).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
    remove.mockRestore();
  });
});
