import type { Data, Layout } from "plotly.js";
import { fitViewToAspect, pointOnArc, viewForPoints, type GeoView } from "../../lib/geo";
import { COLOMBIA_BOUNDS } from "../airports/coordinates";
import { formatDuration, formatTravelDate } from "../../lib/format";
import type { Airport } from "../../types/airport";
import { toPoint, type MapRoute } from "./routes";

/**
 * Plotly no puede leer variables CSS, así que los colores del mapa se
 * repiten aquí. Deben mantenerse alineados con los tokens `--map-*` de
 * styles/tokens.css.
 */
export const MAP_COLORS = {
  ocean: "#0b1626",
  land: "#16263d",
  border: "#34506f",
  airport: "#8aa4c4",
  route: "#60a5fa",
  routeActive: "#ffffff",
  origin: "#60a5fa",
  destination: "#ffffff",
  label: "#cbd8ea",
  night: "#0b1220",
} as const;

/** Posición fija de cada traza: permite actualizar solo la del avión animado. */
export const TRACE = {
  airports: 0,
  routes: 1,
  glow: 2,
  selected: 3,
  routeAirports: 4,
  endpoints: 5,
  planes: 6,
  activePlane: 7,
} as const;

/** El avión no se dibuja en los extremos para no tapar origen y destino. */
export const PLANE_MIN_T = 0.1;
export const PLANE_MAX_T = 0.9;
export const PLANE_REST_T = 0.5;

export const DEFAULT_ASPECT = 1.5;

/**
 * Vista inicial fija sobre Colombia. No se calcula a partir de los
 * aeropuertos: un solo dato atípico (o un aeropuerto extranjero) la
 * convertiría en un mapamundi.
 */
export function colombiaView(aspect: number = DEFAULT_ASPECT): GeoView {
  // Margen para que San Andrés y la costa no queden pegados al borde; arriba
  // es mayor porque los botones del mapa cubren esa franja.
  return fitViewToAspect(
    {
      lonRange: [COLOMBIA_BOUNDS.lonMin - 1, COLOMBIA_BOUNDS.lonMax + 1],
      latRange: [COLOMBIA_BOUNDS.latMin - 1, COLOMBIA_BOUNDS.latMax + 2.5],
    },
    aspect,
  );
}

export interface FigureInput {
  airports: Airport[];
  routes: MapRoute[];
  selectedId: string | null;
  /** Ancho / alto del contenedor del mapa; ajusta el encuadre para llenarlo. */
  aspect?: number;
  /**
   * Cambia cuando la cámara debe volver a encuadrar (otra selección, "Vista
   * general"). Mientras sea igual, Plotly conserva el zoom que haga el usuario.
   */
  viewKey?: string;
}

export interface MapFigure {
  data: Data[];
  layout: Partial<Layout>;
  overview: GeoView | null;
}

/**
 * @types/plotly.js no cubre todos los atributos de scattergeo (símbolos
 * nuevos, `marker.angle` por punto). Esta es la única puerta de cast del
 * módulo y se usa solo para construir trazas.
 */
const trace = (definition: Record<string, unknown>): Data => definition as unknown as Data;

function routeLabel(route: MapRoute): string {
  const { itinerary, origin, destination } = route;
  return (
    `<b>${origin.iata_code} → ${destination.iata_code}</b><br>` +
    `${origin.city} → ${destination.city}<br>` +
    `${formatTravelDate(itinerary.travel_date)} · ${formatDuration(itinerary.duration_minutes)}`
  );
}

function planeTrace(routes: MapRoute[], size: number, color: string, outline: string, rest = PLANE_REST_T) {
  const places = routes.map((route) => pointOnArc(route.arc, rest));
  return {
    type: "scattergeo",
    mode: "markers",
    lon: places.map((p) => p.lon),
    lat: places.map((p) => p.lat),
    customdata: routes.map((r) => r.itinerary.id),
    text: routes.map(routeLabel),
    hovertemplate: "%{text}<extra></extra>",
    marker: {
      symbol: "arrow-wide",
      size,
      color,
      angle: places.map((p) => p.heading),
      line: { color: outline, width: 1 },
    },
  };
}

export function buildFigure({
  airports,
  routes,
  selectedId,
  aspect = DEFAULT_ASPECT,
  viewKey = "",
}: FigureInput): MapFigure {
  const selected = routes.find((r) => r.itinerary.id === selectedId) ?? null;
  const others = routes.filter((r) => r !== selected);
  const dimmed = selected !== null;

  // Aeropuertos base (todos los que entrega el Airport Service).
  const airportsTrace = {
    type: "scattergeo",
    mode: "markers",
    lon: airports.map((a) => a.longitude),
    lat: airports.map((a) => a.latitude),
    text: airports.map((a) => `<b>${a.name}</b><br>${a.city} · ${a.iata_code}`),
    hovertemplate: "%{text}<extra></extra>",
    marker: { size: 5, color: MAP_COLORS.airport, opacity: 0.85, line: { width: 0 } },
  };

  // Rutas secundarias: una sola traza con huecos (null) entre trayectorias.
  const lon: Array<number | null> = [];
  const lat: Array<number | null> = [];
  const customdata: Array<string | null> = [];
  const text: Array<string | null> = [];
  for (const route of others) {
    const label = routeLabel(route);
    route.arc.lon.forEach((value, i) => {
      lon.push(value);
      lat.push(route.arc.lat[i]);
      customdata.push(route.itinerary.id);
      text.push(label);
    });
    lon.push(null);
    lat.push(null);
    customdata.push(null);
    text.push(null);
  }
  const routesTrace = {
    type: "scattergeo",
    mode: "lines",
    lon,
    lat,
    customdata,
    text,
    hovertemplate: "%{text}<extra></extra>",
    line: { width: 1.8, color: MAP_COLORS.route },
    opacity: dimmed ? 0.35 : 0.8,
  };

  // Ruta activa: halo suave + trazo nítido encima.
  const selectedLon = selected ? selected.arc.lon : [];
  const selectedLat = selected ? selected.arc.lat : [];
  const glowTrace = {
    type: "scattergeo",
    mode: "lines",
    lon: selectedLon,
    lat: selectedLat,
    hoverinfo: "skip",
    line: { width: 9, color: MAP_COLORS.route },
    opacity: 0.22,
  };
  const selectedTrace = {
    type: "scattergeo",
    mode: "lines",
    lon: selectedLon,
    lat: selectedLat,
    hoverinfo: "skip",
    line: { width: 3, color: MAP_COLORS.routeActive },
  };

  // Aeropuertos que forman parte de los itinerarios, con su código IATA.
  const selectedIds = selected ? new Set([selected.origin.id, selected.destination.id]) : new Set<string>();
  const routeAirports = new Map<string, Airport>();
  for (const route of routes) {
    for (const airport of [route.origin, route.destination]) {
      if (!selectedIds.has(airport.id)) routeAirports.set(airport.id, airport);
    }
  }
  const routeAirportList = [...routeAirports.values()];
  const routeAirportsTrace = {
    type: "scattergeo",
    mode: "markers+text",
    lon: routeAirportList.map((a) => a.longitude),
    lat: routeAirportList.map((a) => a.latitude),
    text: routeAirportList.map((a) => a.iata_code),
    textposition: "top center",
    textfont: { size: 10, color: MAP_COLORS.label, family: "ui-monospace, Menlo, Consolas, monospace" },
    hovertemplate: "%{customdata}<extra></extra>",
    customdata: routeAirportList.map((a) => `<b>${a.name}</b><br>${a.city} · ${a.iata_code}`),
    marker: { size: 8, color: MAP_COLORS.route, line: { color: MAP_COLORS.night, width: 1.5 } },
  };

  // Origen (círculo) y destino (rombo) de la ruta seleccionada: se distinguen por forma, no solo por color.
  const endpoints = selected ? [selected.origin, selected.destination] : [];
  const endpointsTrace = {
    type: "scattergeo",
    mode: "markers+text",
    lon: endpoints.map((a) => a.longitude),
    lat: endpoints.map((a) => a.latitude),
    text: endpoints.map((a) => `<b>${a.iata_code}</b>`),
    textposition: "top center",
    textfont: { size: 12, color: "#ffffff", family: "ui-monospace, Menlo, Consolas, monospace" },
    hovertemplate: "%{customdata}<extra></extra>",
    customdata: endpoints.map(
      (a, i) => `<b>${a.name}</b><br>${a.city} · ${a.iata_code}<br>${i === 0 ? "Origen" : "Destino"}`,
    ),
    marker: {
      size: 13,
      symbol: ["circle", "diamond"],
      color: [MAP_COLORS.origin, MAP_COLORS.destination],
      line: { color: MAP_COLORS.night, width: 2 },
    },
  };

  const planes = planeTrace(others, 15, MAP_COLORS.label, MAP_COLORS.night);
  const activePlane = planeTrace(selected ? [selected] : [], 22, MAP_COLORS.routeActive, MAP_COLORS.route);

  const overview = colombiaView(aspect);
  const view = viewForSelection(routes, selectedId, overview, aspect);

  const layout: Partial<Layout> = {
    showlegend: false,
    margin: { t: 0, b: 0, l: 0, r: 0 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    dragmode: "pan",
    uirevision: `${selectedId ?? "general"}|${viewKey}|${aspect}`,
    hoverlabel: {
      bgcolor: MAP_COLORS.night,
      bordercolor: "#2b4262",
      font: { color: "#e6edf7", size: 12 },
    },
    geo: {
      scope: "south america",
      projection: { type: "mercator" },
      ...(view ? { lonaxis: { range: view.lonRange }, lataxis: { range: view.latRange } } : {}),
      resolution: 50,
      showland: true,
      landcolor: MAP_COLORS.land,
      showocean: true,
      oceancolor: MAP_COLORS.ocean,
      showcountries: true,
      countrycolor: MAP_COLORS.border,
      countrywidth: 0.8,
      showcoastlines: true,
      coastlinecolor: MAP_COLORS.border,
      coastlinewidth: 0.8,
      showlakes: false,
      showframe: false,
      bgcolor: "rgba(0,0,0,0)",
    } as Partial<Layout["geo"]>,
  };

  // El orden de esta lista debe coincidir con TRACE.
  const data = [
    airportsTrace,
    routesTrace,
    glowTrace,
    selectedTrace,
    routeAirportsTrace,
    endpointsTrace,
    planes,
    activePlane,
  ].map(trace);

  return { data, layout, overview };
}

/** Encuadre al seleccionar una ruta; sin selección, vuelve a la vista general. */
export function viewForSelection(
  routes: MapRoute[],
  selectedId: string | null,
  overview: GeoView | null,
  aspect: number = DEFAULT_ASPECT,
): GeoView | null {
  const selected = routes.find((r) => r.itinerary.id === selectedId);
  if (!selected) return overview;
  const view = viewForPoints([toPoint(selected.origin), toPoint(selected.destination)], 0.35, 3);
  return view ? fitViewToAspect(view, aspect) : overview;
}
