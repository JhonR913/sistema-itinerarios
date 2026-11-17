import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TopBar } from "./TopBar";

vi.mock("../auth/SessionMenu", () => ({
  SessionMenu: () => <div data-testid="session-menu">Estado de sesión</div>,
}));

describe("TopBar", () => {
  it("presenta la identidad del sistema y el enlace de marca al mapa", () => {
    render(<TopBar />);

    const brand = screen.getByRole("link", { name: "Sistema de Itinerarios Personales" });
    expect(brand.getAttribute("href")).toBe("#mapa");
    expect(brand.textContent).toContain("Itinerarios");
    expect(brand.textContent).toContain("Personales");
  });

  it("ofrece navegación a Mapa e Itinerarios y muestra el menú de sesión", () => {
    render(<TopBar />);

    const navigation = screen.getByRole("navigation", { name: "Secciones" });
    expect(within(navigation).getByRole("link", { name: "Mapa" }).getAttribute("href")).toBe("#mapa");
    expect(within(navigation).getByRole("link", { name: "Itinerarios" }).getAttribute("href")).toBe("#itinerarios");
    expect(screen.getByTestId("session-menu").textContent).toBe("Estado de sesión");
  });
});
