/**
 * usuario@dominio.tld sin espacios. Se evita a propósito la regex clásica
 * (dos grupos "cualquier cosa menos @ y espacio" separados por un punto): tiene
 * backtracking super-lineal. Esta versión es lineal.
 */
export function isValidEmail(value: string): boolean {
  const at = value.indexOf("@");
  if (at < 1 || value.includes("@", at + 1)) return false;
  if (/\s/.test(value)) return false;
  const domain = value.slice(at + 1);
  return domain.slice(1, -1).includes("."); // un punto que no sea el primero ni el último
}
