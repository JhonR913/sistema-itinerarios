import { memo, useMemo, useRef } from "react";
import { useElementAspect } from "../../lib/useElementAspect";
import type { Airport } from "../../types/airport";
import { Plot, TOPOJSON_URL } from "../map/plotly";
import { DEFAULT_ASPECT, buildFigure } from "../map/figure";
import type { MapRoute } from "../map/routes";
import { useRouteAnimation } from "../map/useRouteAnimation";

interface AirportMapProps {
  airports: Airport[];
  routes: MapRoute[];
  selectedId: string | null;
  onSelect: (itineraryId: string) => void;
  animationEnabled: boolean;
  /** Cada cambio devuelve la cámara a la vista general. */
  viewResetKey: number;
}

const MODEBAR_BUTTONS: Array<Array<"zoomInGeo" | "zoomOutGeo" | "resetGeo">> = [
  ["zoomInGeo", "zoomOutGeo", "resetGeo"],
];

let figureRevision = 0;

/**
 * RF-003: mapa interactivo con Plotly. Solo dibuja: no hace fetch ni conoce
 * la URL del backend. Recibe aeropuertos y rutas ya resueltos.
 */
function AirportMapComponent({
  airports,
  routes,
  selectedId,
  onSelect,
  animationEnabled,
  viewResetKey,
}: AirportMapProps) {
  const graphRef = useRef<HTMLElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const aspect = useElementAspect(wrapperRef, DEFAULT_ASPECT);

  const figure = useMemo(() => {
    figureRevision += 1;
    return { ...buildFigure({ airports, routes, selectedId, aspect, viewKey: String(viewResetKey) }), revision: figureRevision };
  }, [airports, routes, selectedId, aspect, viewResetKey]);

  const selectedRoute = useMemo(
    () => routes.find((r) => r.itinerary.id === selectedId) ?? null,
    [routes, selectedId],
  );

  useRouteAnimation(graphRef, selectedRoute, animationEnabled);

  return (
    <div className="map-fill" ref={wrapperRef}>
      {airports.length === 0 ? (
        <p className="map-empty">No hay aeropuertos para mostrar todavía.</p>
      ) : (
        <Plot
          data={figure.data}
          layout={figure.layout}
          revision={figure.revision}
          config={{
            displayModeBar: true,
            displaylogo: false,
            responsive: true,
            scrollZoom: false,
            modeBarButtons: MODEBAR_BUTTONS,
          topojsonURL: TOPOJSON_URL,
          }}
          useResizeHandler
          className="map-plot"
          style={{ width: "100%", height: "100%" }}
          onInitialized={(_figure, graph) => {
            graphRef.current = graph as HTMLElement;
          }}
          onUpdate={(_figure, graph) => {
            graphRef.current = graph as HTMLElement;
          }}
          onClick={(event) => {
            const id = event.points?.[0]?.customdata;
            if (typeof id === "string") onSelect(id);
          }}
        />
      )}
    </div>
  );
}

export const AirportMap = memo(AirportMapComponent);
