import { useEffect, type MutableRefObject } from "react";
import { pointOnArc } from "../../lib/geo";
import { Plotly } from "./plotly";
import { PLANE_MAX_T, PLANE_MIN_T, PLANE_REST_T, TRACE } from "./figure";
import type { MapRoute } from "./routes";

const LOOP_MS = 9000;
export const ANIMATION_FPS = 15; // suficiente para un avión pequeño y mucho más barato que 24+
const FRAME_MS = 1000 / ANIMATION_FPS;

/**
 * Desplaza un avión sobre la ruta seleccionada. Solo actualiza la traza del
 * avión con `Plotly.restyle` (no redibuja el mapa) y se detiene al
 * desmontar, al cambiar de ruta o al desactivar la animación.
 *
 * Es una animación decorativa de un itinerario guardado: no representa la
 * posición real de ningún vuelo.
 */
export function useRouteAnimation(
  graphRef: MutableRefObject<HTMLElement | null>,
  route: MapRoute | null,
  enabled: boolean,
): void {
  useEffect(() => {
    const graph = graphRef.current;
    if (!route || !graph) return;

    // Una sola actualización de Plotly en curso: si la anterior no terminó se
    // salta el cuadro, así no se acumulan llamadas cuando el mapa va lento.
    let busy = false;
    const place = (t: number) => {
      const target = graphRef.current;
      if (!target || busy) return;
      busy = true;
      const p = pointOnArc(route.arc, t);
      void Plotly.restyle(
        target,
        { lon: [[p.lon]], lat: [[p.lat]], "marker.angle": [[p.heading]] },
        [TRACE.activePlane],
      ).finally(() => {
        busy = false;
      });
    };

    if (!enabled) {
      place(PLANE_REST_T);
      return;
    }

    let frameId = 0;
    let last = 0;
    let elapsed = 0; // tiempo de animación acumulado; no avanza con la pestaña oculta
    let previous = performance.now();

    const tick = (now: number) => {
      frameId = requestAnimationFrame(tick);
      if (now - last < FRAME_MS) return;
      elapsed += now - previous;
      previous = now;
      last = now;
      const progress = (elapsed % LOOP_MS) / LOOP_MS;
      place(PLANE_MIN_T + progress * (PLANE_MAX_T - PLANE_MIN_T));
    };

    // Con la pestaña oculta no se anima; al volver se retoma sin salto.
    const onVisibility = () => {
      cancelAnimationFrame(frameId);
      if (document.hidden) return;
      previous = performance.now();
      frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelAnimationFrame(frameId);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [graphRef, route, enabled]);
}
