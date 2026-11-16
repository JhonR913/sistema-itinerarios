/** Mismas reglas que el servidor (el servidor es quien manda; esto solo evita idas y vueltas). */
export const MIN_PASSWORD_LENGTH = 10;
const MAX_PASSWORD_LENGTH = 128;

export function passwordProblem(password: string, email = ""): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) return `La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`;
  if (password.length > MAX_PASSWORD_LENGTH) return "La contraseña es demasiado larga.";
  if (new Set(password).size < 4) return "La contraseña es demasiado simple.";
  if (email && password.toLowerCase() === email.trim().toLowerCase()) return "La contraseña no puede ser tu correo.";
  return null;
}

export function isValidCode(code: string): boolean {
  return code.length === 6 && [...code].every((c) => c >= "0" && c <= "9");
}
