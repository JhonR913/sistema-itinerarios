/**
 * Utilidades geográficas puras (sin React ni Plotly) para dibujar rutas
 * aéreas. Todo se calcula a partir de coordenadas reales de aeropuertos;
 * aquí no hay datos propios ni constantes de lugares.
 */

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface Arc {
  lat: number[];
  lon: number[];
}

export interface GeoView {
  lonRange: [number, number];
  latRange: [number, number];
}

const toRad = (deg: number) => (deg * Math.PI) / 180;
const toDeg = (rad: number) => (rad * 180) / Math.PI;

/**
 * Trayectoria de círculo máximo entre dos puntos (interpolación esférica).
 * Es la ruta más corta sobre la Tierra, por eso se ve curva en la proyección.
 */
export function greatCircleArc(from: GeoPoint, to: GeoPoint, steps = 64): Arc {
  const lat1 = toRad(from.lat);
  const lon1 = toRad(from.lon);
  const lat2 = toRad(to.lat);
  const lon2 = toRad(to.lon);

  // Distancia angular (fórmula haversine).
  const d =
    2 *
    Math.asin(
      Math.sqrt(
        Math.sin((lat2 - lat1) / 2) ** 2 +
          Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2,
      ),
    );

  // Puntos coincidentes: no hay trayectoria que interpolar.
  if (d < 1e-9) {
    return { lat: [from.lat, to.lat], lon: [from.lon, to.lon] };
  }

  const lats: number[] = [];
  const lons: number[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const f = i / steps;
    const a = Math.sin((1 - f) * d) / Math.sin(d);
    const b = Math.sin(f * d) / Math.sin(d);
    const x = a * Math.cos(lat1) * Math.cos(lon1) + b * Math.cos(lat2) * Math.cos(lon2);
    const y = a * Math.cos(lat1) * Math.sin(lon1) + b * Math.cos(lat2) * Math.sin(lon2);
    const z = a * Math.sin(lat1) + b * Math.sin(lat2);
    lats.push(toDeg(Math.atan2(z, Math.sqrt(x * x + y * y))));
    lons.push(toDeg(Math.atan2(y, x)));
  }

  // Los extremos se fijan a los valores originales para evitar error de redondeo.
  lats[0] = from.lat;
  lons[0] = from.lon;
  lats[steps] = to.lat;
  lons[steps] = to.lon;

  return { lat: lats, lon: unwrapLongitudes(lons) };
}

/** Evita saltos de ±360° cuando una ruta cruza el antimeridiano. */
function unwrapLongitudes(lons: number[]): number[] {
  const result = [lons[0]];
  for (let i = 1; i < lons.length; i += 1) {
    let lon = lons[i];
    const prev = result[i - 1];
    while (lon - prev > 180) lon -= 360;
    while (lon - prev < -180) lon += 360;
    result.push(lon);
  }
  return result;
}

/** Rumbo inicial en grados, en sentido horario desde el norte (0–360). */
export function bearing(from: GeoPoint, to: GeoPoint): number {
  const lat1 = toRad(from.lat);
  const lat2 = toRad(to.lat);
  const dLon = toRad(to.lon - from.lon);
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

const mercatorYOf = (latDeg: number) => Math.log(Math.tan(Math.PI / 4 + toRad(latDeg) / 2));

/**
 * Ángulo con el que se ve un tramo en un mapa Mercator: grados en sentido
 * horario desde "arriba" de la pantalla. Es lo que necesita un marcador
 * rotado en pantalla; difiere un poco del rumbo geográfico real porque
 * Mercator deforma las distancias, no los ángulos locales.
 */
export function screenHeading(from: GeoPoint, to: GeoPoint): number {
  const dx = toRad(to.lon - from.lon);
  const dy = mercatorYOf(to.lat) - mercatorYOf(from.lat);
  return (toDeg(Math.atan2(dx, dy)) + 360) % 360;
}

export interface PointOnArc extends GeoPoint {
  /** Ángulo en pantalla (ver `screenHeading`), listo para `marker.angle`. */
  heading: number;
}

/** Posición y rumbo en la fracción `t` (0–1) de una trayectoria ya calculada. */
export function pointOnArc(arc: Arc, t: number): PointOnArc {
  const last = arc.lat.length - 1;
  const clamped = Math.min(1, Math.max(0, t));
  const position = clamped * last;
  const i = Math.min(Math.floor(position), last - 1);
  const frac = position - i;

  const lat = arc.lat[i] + (arc.lat[i + 1] - arc.lat[i]) * frac;
  const lon = arc.lon[i] + (arc.lon[i + 1] - arc.lon[i]) * frac;
  const heading = screenHeading(
    { lat: arc.lat[i], lon: arc.lon[i] },
    { lat: arc.lat[i + 1], lon: arc.lon[i + 1] },
  );
  return { lat, lon, heading };
}

/**
 * Encuadre que contiene todos los puntos dados, con margen proporcional y un
 * tamaño mínimo para que un único aeropuerto no produzca un zoom absurdo.
 */
export function viewForPoints(points: GeoPoint[], paddingRatio = 0.25, minSpan = 6): GeoView | null {
  if (points.length === 0) return null;

  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);

  const latSpan = Math.max(maxLat - minLat, minSpan);
  const lonSpan = Math.max(maxLon - minLon, minSpan);
  const latCenter = (maxLat + minLat) / 2;
  const lonCenter = (maxLon + minLon) / 2;

  const halfLat = (latSpan * (1 + paddingRatio * 2)) / 2;
  const halfLon = (lonSpan * (1 + paddingRatio * 2)) / 2;

  return {
    latRange: [Math.max(-85, latCenter - halfLat), Math.min(85, latCenter + halfLat)],
    lonRange: [lonCenter - halfLon, lonCenter + halfLon],
  };
}

const mercatorY = mercatorYOf;
const inverseMercatorY = (y: number) => toDeg(2 * Math.atan(Math.exp(y)) - Math.PI / 2);

/**
 * Amplía el encuadre (sin recortarlo) hasta que su proporción coincida con la
 * del contenedor. Sin esto, Plotly deja franjas vacías a los lados cuando la
 * zona de datos es más alta o más ancha que el mapa.
 */
export function fitViewToAspect(view: GeoView, aspect: number): GeoView {
  if (!Number.isFinite(aspect) || aspect <= 0) return view;

  const lonCenter = (view.lonRange[0] + view.lonRange[1]) / 2;
  const lonSpan = toRad(view.lonRange[1] - view.lonRange[0]);
  const y1 = mercatorY(view.latRange[0]);
  const y2 = mercatorY(view.latRange[1]);
  const ySpan = y2 - y1;
  if (lonSpan <= 0 || ySpan <= 0) return view;

  if (lonSpan / ySpan < aspect) {
    const halfLon = toDeg((ySpan * aspect) / 2);
    return { lonRange: [lonCenter - halfLon, lonCenter + halfLon], latRange: view.latRange };
  }

  const yCenter = (y1 + y2) / 2;
  const halfY = lonSpan / aspect / 2;
  return {
    lonRange: view.lonRange,
    latRange: [Math.max(-85, inverseMercatorY(yCenter - halfY)), Math.min(85, inverseMercatorY(yCenter + halfY))],
  };
}
