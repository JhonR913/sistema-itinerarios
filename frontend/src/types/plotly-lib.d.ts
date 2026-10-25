/**
 * Módulos parciales de plotly.js (core + un solo tipo de traza) para no
 * empaquetar los ~40 tipos de gráfico que este proyecto no usa. @types/plotly.js
 * no los tipa, así que se declara solo lo que usa el mapa.
 */
declare module "plotly.js/lib/core" {
  interface PlotlyCore {
    register(modules: unknown[]): void;
    restyle(graphDiv: HTMLElement, update: Record<string, unknown>, traces?: number | number[]): Promise<unknown>;
    relayout(graphDiv: HTMLElement, update: Record<string, unknown>): Promise<unknown>;
  }
  const Plotly: PlotlyCore;
  export default Plotly;
}

declare module "plotly.js/lib/scattergeo" {
  const scattergeo: unknown;
  export default scattergeo;
}
