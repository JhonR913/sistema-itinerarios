#!/usr/bin/env python3
"""Sustituto LOCAL de Mailpit para ejecutar sin Docker: recibe SMTP y expone
el subconjunto de la API de Mailpit que usan las pruebas
(GET /api/v1/messages, DELETE /api/v1/messages).

  pip install aiosmtpd==1.4.6
  python3 tools/smtp_sink.py [smtp=1025] [http=8025]

En Docker Compose se usa Mailpit real (axllent/mailpit); este script es solo
para entornos sin Docker. No es Mailpit y no lo reemplaza en la demostracion.
"""
import json
import sys
import threading
from email import message_from_bytes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from aiosmtpd.controller import Controller

MESSAGES = []


class Sink:
    async def handle_DATA(self, server, session, envelope):  # noqa: N802
        msg = message_from_bytes(envelope.content)
        MESSAGES.append({
            "ID": str(len(MESSAGES) + 1),
            "From": {"Address": envelope.mail_from},
            "To": [{"Address": a} for a in envelope.rcpt_tos],
            "Subject": msg["Subject"],
            "Snippet": (msg.get_payload() or "")[:120],
        })
        return "250 OK"


class Api(BaseHTTPRequestHandler):
    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/v1/messages"):
            self._send(200, {"total": len(MESSAGES), "messages": MESSAGES})
        else:
            self._send(404, {"error": "not found"})

    def do_DELETE(self):  # noqa: N802
        MESSAGES.clear()
        self._send(200, {"ok": True})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    smtp_port = int(sys.argv[1]) if len(sys.argv) > 1 else 1025
    http_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8025
    Controller(Sink(), hostname="0.0.0.0", port=smtp_port).start()  # nosec B104
    print(f"SMTP en :{smtp_port}, API tipo Mailpit en :{http_port} (SUMIDERO LOCAL, no es Mailpit)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", http_port), Api).serve_forever()  # nosec B104
    threading.Event().wait()
