import { useEffect, useState, type RefObject } from "react";

/**
 * Proporción ancho/alto de un elemento, redondeada a pasos de 0.1 para no
 * volver a calcular el mapa por cada píxel de un redimensionamiento.
 */
export function useElementAspect(ref: RefObject<HTMLElement>, fallback: number): number {
  const [aspect, setAspect] = useState(fallback);

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === "undefined") return;

    const measure = () => {
      const { width, height } = element.getBoundingClientRect();
      if (width > 0 && height > 0) {
        setAspect(Math.round((width / height) * 10) / 10);
      }
    };
    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);

  return aspect;
}
