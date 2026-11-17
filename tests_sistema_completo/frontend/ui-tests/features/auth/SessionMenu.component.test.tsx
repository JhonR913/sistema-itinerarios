import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionMenu } from "./SessionMenu";
import { useAuth } from "./authContextValue";
import { LOGIN_INPUT_ID } from "./constants";

vi.mock("./authContextValue", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

function mockAuth(username: string | null, logout: () => Promise<void> = vi.fn(async () => {})) {
  mockedUseAuth.mockReturnValue({
    token: username ? "test-access-token" : null,
    username,
    email: username ? "pruebas@example.test" : null,
    restoring: false,
    startSession: vi.fn(),
    logout,
  });
  return logout;
}

describe("SessionMenu", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => cleanup());

  it("muestra el botón de inicio de sesión cuando no hay usuario", () => {
    mockAuth(null);
    render(<SessionMenu />);

    expect(screen.getByRole("button", { name: /iniciar sesión/i })).toBeTruthy();
  });

  it("lleva el foco al campo de usuario al pulsar Iniciar sesión", () => {
    mockAuth(null);
    render(
      <>
        <input id={LOGIN_INPUT_ID} aria-label="Usuario" />
        <SessionMenu />
      </>,
    );

    fireEvent.click(screen.getByRole("button", { name: /iniciar sesión/i }));
    expect(document.activeElement).toBe(document.getElementById(LOGIN_INPUT_ID));
  });

  it("muestra el nombre y la inicial cuando existe una sesión", () => {
    mockAuth("María");
    const { container } = render(<SessionMenu />);

    expect(container.querySelector(".session__name")?.textContent).toContain("María");
    expect(container.querySelector(".session__avatar")?.textContent).toBe("M");
    expect(container.querySelector(".visually-hidden")?.textContent).toContain("Sesión iniciada como");
  });

  it("invoca el cierre de sesión al pulsar Cerrar sesión", () => {
    const logout = mockAuth("María");
    render(<SessionMenu />);

    fireEvent.click(screen.getByRole("button", { name: /cerrar sesión/i }));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
