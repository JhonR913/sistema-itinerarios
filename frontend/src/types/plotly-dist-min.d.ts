/**
 * plotly.js-dist-min no publica tipos. Se declara solo la parte de la API
 * que usa el mapa (restyle para animar un avión, relayout para el encuadre).
 */
declare module "plotly.js-dist-min" {
  interface PlotlyApi {
    restyle(graphDiv: HTMLElement, update: Record<string, unknown>, traces?: number | number[]): Promise<unknown>;
    relayout(graphDiv: HTMLElement, update: Record<string, unknown>): Promise<unknown>;
  }
  const Plotly: PlotlyApi;
  export default Plotly;
}
