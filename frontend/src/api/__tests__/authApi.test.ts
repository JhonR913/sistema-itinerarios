import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../lib/httpClient";
import { authApi } from "../authApi";

function mockFetch(status = 200, body: unknown = { access_token: "t", token_type: "bearer", expires_in_minutes: 30 }) {
  const fn = vi.fn().mockImplementation(async () => new Response(status === 204 ? null : JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("authApi", () => {
  it("registra con correo, nombre y contraseña", async () => {
    const fetchMock = mockFetch(202, { message: "ok" });
    await authApi.register("ana@example.com", "Ana", "clave-segura-123");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/register");
    expect(JSON.parse(init.body)).toEqual({ email: "ana@example.com", name: "Ana", password: "clave-segura-123" });
  });

  it("verifica el código y manda las credenciales de cookie solo al mismo sitio", async () => {
    const fetchMock = mockFetch();
    await authApi.verify("ana@example.com", "123456");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/verify");
    expect(init.credentials).toBe("same-origin");
    expect(JSON.parse(init.body)).toEqual({ email: "ana@example.com", code: "123456" });
  });

  it("login, refresh y logout usan POST sin guardar nada en el navegador", async () => {
    const fetchMock = mockFetch();
    await authApi.login("ana@example.com", "clave-segura-123");
    await authApi.refresh();
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(["/api/auth/login", "/api/auth/refresh"]);
    expect(fetchMock.mock.calls[1][1].body).toBeUndefined();
  });

  it("olvido y restablecimiento", async () => {
    const fetchMock = mockFetch(204, null);
    await authApi.forgot("ana@example.com");
    await authApi.reset("ana@example.com", "123456", "nueva-clave-segura-9");
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(["/api/auth/forgot", "/api/auth/reset"]);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      email: "ana@example.com", code: "123456", password: "nueva-clave-segura-9",
    });
  });

  it("propaga el mensaje y el código estable del servidor", async () => {
    mockFetch(403, { detail: "Debes verificar tu correo", code: "EMAIL_NOT_VERIFIED" });
    const err = await authApi.login("ana@example.com", "x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 403, code: "EMAIL_NOT_VERIFIED", message: "Debes verificar tu correo" });
  });

  it("errores sin cuerpo JSON no rompen", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 502 })));
    await expect(authApi.refresh()).rejects.toMatchObject({ status: 502, message: "Error 502" });
  });
});
