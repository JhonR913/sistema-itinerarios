import { afterEach, describe, expect, it, vi } from "vitest";
import { authApi } from "../authApi";

function mockFetch() {
  const fn = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ access_token: "t", token_type: "bearer", expires_in_minutes: 60 }), { status: 200 }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("authApi.issueToken", () => {
  it("envia solo username cuando no hay correo", async () => {
    const fetchMock = mockFetch();
    await authApi.issueToken("jhon");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ username: "jhon" });
  });

  it("incluye el correo cuando se indica", async () => {
    const fetchMock = mockFetch();
    await authApi.issueToken("jhon", "jhon@example.com");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ username: "jhon", email: "jhon@example.com" });
  });
});
