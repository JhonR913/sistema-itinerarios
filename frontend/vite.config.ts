/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // El chunk del mapa (Plotly, ~1.3 MB) se carga bajo demanda con import()
    // dinamico; el bundle inicial es ~170 KB. El limite evita un aviso que no
    // aplica a ese chunk perezoso.
    chunkSizeWarningLimit: 1500,
  },
  test: {
    environment: "jsdom",
    globals: true,
    coverage: { provider: "v8", reporter: ["text-summary", "lcov"], include: ["src/**/*.{ts,tsx}"], exclude: ["src/**/*.d.ts", "src/main.tsx"] },
  },
});
