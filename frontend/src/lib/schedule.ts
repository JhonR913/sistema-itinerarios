/**
 * Utilidades de agenda del viajero. Las reglas replican (solo para dar
 * respuesta inmediata) las que el servidor aplica de forma definitiva:
 *   - un vuelo no puede traslaparse con otro tuyo,
 *   - debe salir desde donde aterrizó tu vuelo anterior,
 *   - debe terminar donde sale tu vuelo siguiente.
 * Si el servidor discrepa, manda el servidor (responde 409 con el motivo).
 */
import type { Airport } from "../types/airport";
import type { Itinerary } from "../types/itinerary";

/** Colombia está en UTC-5 todo el año (sin horario de verano). */
const UTC_OFFSET_HOURS = -5;
const TIME_ZONE = "America/Bogota";

/** "2026-12-01T06:00" (hora local de Colombia) -> "2026-12-01T06:00:00-05:00". */
export function toDepartureIso(localValue: string): string {
  return `${localValue}:00-05:00`;
}

/** Valor para <input type="datetime-local"> con la hora actual de Colombia. */
export function nowLocalInputValue(now: Date = new Date()): string {
  return new Date(now.getTime() + UTC_OFFSET_HOURS * 3_600_000).toISOString().slice(0, 16);
}

const dateTimeFmt = new Intl.DateTimeFormat("es-CO", {
  timeZone: TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const timeFmt = new Intl.DateTimeFormat("es-CO", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit", hour12: false });

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateTimeFmt.format(d);
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : timeFmt.format(d);
}

const toRad = (deg: number) => (deg * Math.PI) / 180;

/** Distancia entre dos aeropuertos (círculo máximo, km). */
export function distanceKm(a: Pick<Airport, "latitude" | "longitude">, b: Pick<Airport, "latitude" | "longitude">): number {
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

/**
 * Duración ESTIMADA (no es un horario real de aerolínea): distancia a
 * ~700 km/h más 30 min de rodaje/ascenso/descenso, redondeada a 5 min.
 * El usuario puede ajustarla antes de guardar.
 */
export function estimateDurationMinutes(a: Airport, b: Airport): number {
  const minutes = (distanceKm(a, b) / 700) * 60 + 30;
  return Math.max(30, Math.round(minutes / 5) * 5);
}

export interface Candidate {
  originId: string;
  destinationId: string;
  departureMs: number;
  durationMinutes: number;
  /** Para editar: ignorar el propio itinerario. */
  ignoreId?: string;
}

const fmt = (iso: string | number) => formatDateTime(new Date(iso).toISOString());

/** Devuelve el motivo del conflicto, o null si la agenda es coherente. */
export function describeConflict(candidate: Candidate, itineraries: Itinerary[], minConnectionMinutes = 0): string | null {
  const buf = minConnectionMinutes * 60_000;
  const start = candidate.departureMs;
  const end = start + candidate.durationMinutes * 60_000;
  const others = itineraries
    .filter((i) => i.id !== candidate.ignoreId)
    .map((i) => ({ it: i, dep: Date.parse(i.departure_at), arr: Date.parse(i.arrival_at) }))
    .sort((x, y) => x.dep - y.dep);

  for (const o of others) {
    if (start < o.arr + buf && o.dep < end + buf) {
      return `Se cruza con tu vuelo ${o.it.origin.city} → ${o.it.destination.city} (${fmt(o.dep)} a ${formatTime(o.it.arrival_at)}).`;
    }
  }
  const before = others.filter((o) => o.arr + buf <= start);
  const prev = before.length ? before.reduce((a, b) => (b.arr > a.arr ? b : a)) : null;
  if (prev && prev.it.destination.airport_id !== candidate.originId) {
    return `Tu vuelo anterior llega a ${prev.it.destination.city} (${fmt(prev.arr)}); desde ahí es donde puedes salir.`;
  }
  const after = others.filter((o) => end + buf <= o.dep);
  const next = after.length ? after.reduce((a, b) => (b.dep < a.dep ? b : a)) : null;
  if (next && next.it.origin.airport_id !== candidate.destinationId) {
    return `Tu siguiente vuelo sale de ${next.it.origin.city} (${fmt(next.dep)}); este vuelo debe terminar allí.`;
  }
  return null;
}

export interface Availability {
  airportId: string;
  city: string;
  iata: string;
  /** Instante (ISO) desde el cual puedes salir de esa ciudad. */
  availableAt: string;
}

/** Dónde estarás tras tu último vuelo y desde cuándo puedes volver a salir. */
export function nextAvailability(itineraries: Itinerary[]): Availability | null {
  if (itineraries.length === 0) return null;
  const last = itineraries.reduce((a, b) => (Date.parse(b.arrival_at) > Date.parse(a.arrival_at) ? b : a));
  return {
    airportId: last.destination.airport_id,
    city: last.destination.city,
    iata: last.destination.iata_code,
    availableAt: last.arrival_at,
  };
}

/** Texto tipo "en 5 h 20 min" / "en 2 días"; null si ya pasó. */
export function timeUntil(iso: string, now: Date = new Date()): string | null {
  const diff = Date.parse(iso) - now.getTime();
  if (!Number.isFinite(diff) || diff <= 0) return null;
  const minutes = Math.round(diff / 60_000);
  if (minutes < 60) return `en ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `en ${hours} h ${minutes % 60} min`;
  const days = Math.floor(hours / 24);
  return `en ${days} ${days === 1 ? "día" : "días"}`;
}
