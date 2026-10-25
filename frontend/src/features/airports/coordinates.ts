import type { Airport } from "../../types/airport";

/** Caja que contiene Colombia continental e insular (San Andrés y Providencia). */
export const COLOMBIA_BOUNDS = { latMin: -5, latMax: 13.5, lonMin: -82, lonMax: -66 } as const;

/** Un poco más amplia, para decidir si una coordenada "cae en Colombia" al detectar errores. */
const NEAR_COLOMBIA = { latMin: -6, latMax: 14.5, lonMin: -83, lonMax: -65 } as const;

/**
 * Convierte lo que llegue del API a número. Acepta números y cadenas
 * ("4.70", "4,70"); cualquier otra cosa (null, "", NaN, texto) es inválida.
 */
export function toCoordinate(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value.trim().replace(",", "."));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function isValidLatLon(lat: number, lon: number): boolean {
  return Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

const inNearColombia = (lat: number, lon: number) =>
  lat >= NEAR_COLOMBIA.latMin &&
  lat <= NEAR_COLOMBIA.latMax &&
  lon >= NEAR_COLOMBIA.lonMin &&
  lon <= NEAR_COLOMBIA.lonMax;

export interface SanitizedAirports {
  /** Aeropuertos con coordenadas numéricas válidas, listos para dibujar. */
  airports: Airport[];
  /** Aeropuertos que se descartaron por no tener coordenadas utilizables. */
  invalidCount: number;
  /** Aeropuertos cuya latitud/longitud venían invertidas o sin signo y se corrigieron. */
  correctedCount: number;
}

/**
 * Valida las coordenadas de los aeropuertos antes de dibujarlas.
 *
 * - Texto numérico se convierte a número.
 * - Sin dato, NaN, fuera de rango o (0, 0) se descartan: el backend rellena
 *   con 0.0 cuando API Colombia no trae coordenadas, y (0, 0) no es un
 *   aeropuerto colombiano. Nunca se inventa una posición.
 * - Solo si la coordenada original NO está en Colombia pero invertirla (o
 *   cambiarle el signo a la longitud) SÍ la deja en Colombia, se corrige y
 *   se cuenta, para que la interfaz lo informe.
 */
export function sanitizeAirports(airports: Airport[]): SanitizedAirports {
  const valid: Airport[] = [];
  let invalidCount = 0;
  let correctedCount = 0;

  for (const airport of airports) {
    const lat = toCoordinate(airport.latitude as unknown);
    const lon = toCoordinate(airport.longitude as unknown);

    if (lat === null || lon === null || (lat === 0 && lon === 0)) {
      invalidCount += 1;
      continue;
    }

    if (isValidLatLon(lat, lon) && inNearColombia(lat, lon)) {
      valid.push({ ...airport, latitude: lat, longitude: lon });
      continue;
    }

    // Candidatos de corrección, del más al menos probable.
    const candidates: Array<[number, number]> = [
      [lon, lat], // latitud y longitud intercambiadas
      [lat, -lon], // longitud sin signo negativo
      [lon, -lat], // intercambiadas y con un signo perdido
    ];
    const fixed = candidates.find(([a, b]) => isValidLatLon(a, b) && inNearColombia(a, b));
    if (fixed) {
      valid.push({ ...airport, latitude: fixed[0], longitude: fixed[1] });
      correctedCount += 1;
      continue;
    }

    if (isValidLatLon(lat, lon)) {
      // Coordenada válida fuera de Colombia (p. ej. un aeropuerto internacional): se conserva.
      valid.push({ ...airport, latitude: lat, longitude: lon });
    } else {
      invalidCount += 1;
    }
  }

  return { airports: valid, invalidCount, correctedCount };
}
