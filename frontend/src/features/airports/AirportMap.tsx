import Plot from "react-plotly.js";
import type { Airport } from "../../types/airport";

interface AirportMapProps {
  airports: Airport[];
}

/**
 * RF-003: mapa interactivo con Plotly consumiendo Airport Service.
 * Este componente solo sabe dibujar: no hace fetch, no conoce la URL del
 * backend. Recibe los datos ya cargados por el contenedor (AirportMapPage).
 */
export function AirportMap({ airports }: AirportMapProps) {
  if (airports.length === 0) {
    return <p className="empty-state">No hay aeropuertos para mostrar todavía.</p>;
  }

  return (
    <Plot
      data={[
        {
          type: "scattergeo",
          mode: "markers",
          lon: airports.map((a) => a.longitude),
          lat: airports.map((a) => a.latitude),
          text: airports.map((a) => `${a.name} (${a.iata_code}) — ${a.city}`),
          hoverinfo: "text",
          marker: { size: 9, color: "#2563eb" },
        },
      ]}
      layout={{
        geo: {
          scope: "south america",
          center: { lat: 4.5, lon: -74 },
          projection: { scale: 5 },
          showland: true,
          landcolor: "#e5e7eb",
        },
        margin: { t: 10, b: 10, l: 0, r: 0 },
        height: 480,
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
    />
  );
}
