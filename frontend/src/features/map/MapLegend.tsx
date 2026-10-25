interface MapLegendProps {
  hasRoutes: boolean;
  hasSelection: boolean;
}

/** Leyenda HTML sobre el mapa. Cada símbolo se distingue por forma, no solo por color. */
export function MapLegend({ hasRoutes, hasSelection }: MapLegendProps) {
  return (
    <ul className="map-legend" aria-label="Leyenda del mapa">
      <li>
        <span className="legend-mark legend-mark--airport" aria-hidden="true" />
        Aeropuerto
      </li>
      {hasRoutes && (
        <>
          <li>
            <span className="legend-mark legend-mark--route" aria-hidden="true" />
            Itinerario guardado
          </li>
          <li>
            <span className="legend-mark legend-mark--plane" aria-hidden="true" />
            Avión (ilustrativo)
          </li>
        </>
      )}
      {hasSelection && (
        <>
          <li>
            <span className="legend-mark legend-mark--active" aria-hidden="true" />
            Ruta seleccionada
          </li>
          <li>
            <span className="legend-mark legend-mark--origin" aria-hidden="true" />
            Origen
          </li>
          <li>
            <span className="legend-mark legend-mark--destination" aria-hidden="true" />
            Destino
          </li>
        </>
      )}
    </ul>
  );
}
