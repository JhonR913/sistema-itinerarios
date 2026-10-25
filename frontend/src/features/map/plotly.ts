import Plotly from "plotly.js/lib/core";
import scattergeo from "plotly.js/lib/scattergeo";
import createPlotlyComponent from "react-plotly.js/factory";

/**
 * Plotly parcial: núcleo + `scattergeo`, que es la única traza del mapa.
 * El paquete completo (`plotly.js-dist-min`) pesaba ~4,7 MB; este módulo se
 * carga solo con el chunk diferido del mapa.
 */
Plotly.register([scattergeo]);

export { Plotly };
export const Plot = createPlotlyComponent(Plotly);

/**
 * Ruta (relativa, mismo origen) desde la que Plotly lee los topojson del
 * mapa. Los archivos viven en `public/topojson/` y los sirve el mismo Nginx
 * del frontend, así el mapa no depende de cdn.plot.ly.
 */
export const TOPOJSON_URL = "/topojson/";
