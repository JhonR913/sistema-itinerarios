#!/usr/bin/env python3
"""
Hook PreToolUse. Bloquea (no solo sugiere) escrituras peligrosas:
  - Escribir/commitear un .env real (no .env.example).
  - Contenido que coincide con patrones de secretos reales.
Basado en Plan_de_Blindaje_Seguridad.docx, sección 3.2.
"""
import json
import re
import sys

BLOCKED_FILENAMES = re.compile(r"(^|/)\.env($|\.(?!example$)[a-zA-Z0-9]+$)")

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"),
    re.compile(r"postgres(ql)?://[^:]+:[^@]+@"),
    re.compile(r"amqp://[^:]+:[^@]+@"),
]

def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        print("pre_tool_use_security: evento no parseable, dejando pasar", file=sys.stderr)
        sys.exit(0)

    file_path = event.get("file_path") or event.get("path") or ""
    content = event.get("content") or event.get("new_content") or ""
    command = event.get("command") or ""

    if BLOCKED_FILENAMES.search(file_path):
        print(f"BLOQUEADO: intento de escribir/commitear un .env real ({file_path}).", file=sys.stderr)
        sys.exit(1)

    haystack = content if content else command
    for pattern in SECRET_PATTERNS:
        if pattern.search(haystack):
            print("BLOQUEADO: el contenido parece contener un secreto real.", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
