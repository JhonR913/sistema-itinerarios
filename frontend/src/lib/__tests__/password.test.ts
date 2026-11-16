import { describe, expect, it } from "vitest";
import { isValidCode, passwordProblem } from "../password";

describe("passwordProblem", () => {
  it("acepta una contraseña razonable", () => {
    expect(passwordProblem("clave-segura-123", "ana@example.com")).toBeNull();
  });
  it.each(["corta", "aaaaaaaaaaaa", "x".repeat(129)])("rechaza %s", (p) => {
    expect(passwordProblem(p)).not.toBeNull();
  });
  it("rechaza que sea el correo", () => {
    expect(passwordProblem("ana@example.com", " Ana@Example.com ")).toMatch(/correo/);
  });
});

describe("isValidCode", () => {
  it.each(["123456", "000000"])("acepta %s", (c) => expect(isValidCode(c)).toBe(true));
  it.each(["", "12345", "1234567", "12345a", "12 456"])("rechaza %s", (c) => expect(isValidCode(c)).toBe(false));
});
