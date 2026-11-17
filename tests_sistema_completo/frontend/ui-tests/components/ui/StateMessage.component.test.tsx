import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StateMessage } from "./StateMessage";

describe("StateMessage", () => {
  it("muestra el estado de carga con el rol accesible status", () => {
    const { container } = render(<StateMessage variant="loading" title="Cargando aeropuertos" />);

    expect(screen.getByRole("status").textContent).toContain("Cargando aeropuertos");
    expect(container.querySelector(".spinner")).not.toBeNull();
    expect(container.querySelector(".state--loading")).not.toBeNull();
  });

  it("expone los errores como alertas y muestra el mensaje y la acción", () => {
    render(
      <StateMessage
        variant="error"
        title="No se pudieron cargar los itinerarios"
        icon="alert"
        action={<button type="button">Reintentar</button>}
      >
        Comprueba la conexión e inténtalo nuevamente.
      </StateMessage>,
    );

    expect(screen.getByRole("alert").textContent).toContain("No se pudieron cargar los itinerarios");
    expect(screen.getByText("Comprueba la conexión e inténtalo nuevamente.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeTruthy();
  });

  it("muestra el estado vacío y el contenido opcional", () => {
    const { container } = render(
      <StateMessage variant="empty" title="Aún no tienes itinerarios">
        Crea uno para visualizar tu ruta.
      </StateMessage>,
    );

    expect(screen.getByText("Aún no tienes itinerarios")).toBeTruthy();
    expect(screen.getByText("Crea uno para visualizar tu ruta.")).toBeTruthy();
    expect(container.querySelector(".state--empty")).not.toBeNull();
    expect(container.firstElementChild?.getAttribute("role")).toBeNull();
  });
});
