import { describe, expect, it } from "vitest";
import { isValidEmail } from "../email";

describe("isValidEmail", () => {
  it.each(["jhon@example.com", "a@b.co", "primer.apellido+tag@sub.dominio.com.co"])("accepts %s", (v) => {
    expect(isValidEmail(v)).toBe(true);
  });

  it.each(["", "sin-arroba", "a@b", "a b@c.com", "a@b.co\n", "a@@b.co", "@b.co", "a@.co", "a@b."])("rejects %j", (v) => {
    expect(isValidEmail(v)).toBe(false);
  });

  it("is linear on pathological input", () => {
    const t0 = performance.now();
    expect(isValidEmail("a@" + ".".repeat(50_000) + "!".repeat(50_000) + " ")).toBe(false);
    expect(performance.now() - t0).toBeLessThan(500);
  });
});
