#!/usr/bin/env python3
"""Proxy TCP de inyeccion de fallos (solo biblioteca estandar), alternativa
liviana y reproducible a Toxiproxy.

  python3 tools/fault_proxy.py --admin 8099 \
      --listen 18001=localhost:8001 --listen 15432=localhost:5432

Modos por puerto de escucha (cambian en caliente, sin reiniciar):
  pass       reenvia normal
  latency    espera `latency_ms` antes de reenviar cada bloque (ambos sentidos)
  drop       cierra la conexion nada mas aceptarla (conexion rechazada/reset)
  blackhole  acepta y NUNCA responde (provoca timeouts)

Admin HTTP:
  GET  /faults                         -> estado
  POST /faults/<puerto>  {"mode": "latency", "latency_ms": 5000}
  POST /faults/reset                   -> todos en pass
"""
import argparse
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {}          # puerto -> {"mode", "latency_ms", "target"}
LOCK = threading.Lock()


def _pipe(src, dst, port):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            with LOCK:
                mode = STATE[port]["mode"]
                latency = STATE[port]["latency_ms"] if mode == "latency" else 0
            if mode == "drop":
                break                      # corta la conexion existente
            if mode == "blackhole":
                continue                   # traga los datos: el otro extremo se queda esperando
            if latency:
                time.sleep(latency / 1000)
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _handle(client, port):
    with LOCK:
        mode = STATE[port]["mode"]
        host, tport = STATE[port]["target"]
    if mode == "drop":
        client.close()
        return
    if mode == "blackhole":
        try:
            while client.recv(65536):
                pass
        except OSError:
            pass
        client.close()
        return
    try:
        upstream = socket.create_connection((host, tport), timeout=5)
    except OSError:
        client.close()
        return
    with LOCK:
        STATE[port]["conns"].extend([client, upstream])
    threading.Thread(target=_pipe, args=(client, upstream, port), daemon=True).start()
    threading.Thread(target=_pipe, args=(upstream, client, port), daemon=True).start()


def _listen(port):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))  # nosec B104
    srv.listen(128)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=_handle, args=(client, port), daemon=True).start()


class Admin(BaseHTTPRequestHandler):
    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        with LOCK:
            self._send(200, {str(p): {"mode": s["mode"], "latency_ms": s["latency_ms"]} for p, s in STATE.items()})

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        name = self.path.rsplit("/", 1)[-1]
        with LOCK:
            if name == "reset":
                for s in STATE.values():
                    s.update(mode="pass", latency_ms=0)
            elif name.isdigit() and int(name) in STATE and body.get("mode") in ("pass", "latency", "drop", "blackhole"):
                st = STATE[int(name)]
                st.update(mode=body["mode"], latency_ms=int(body.get("latency_ms", 0)))
                if body["mode"] == "drop":     # "se cayo": tambien las conexiones ya abiertas
                    for c in st["conns"]:
                        try:
                            c.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                    st["conns"].clear()
            else:
                return self._send(400, {"error": "puerto o modo invalido"})
        self.do_GET()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin", type=int, default=8099)
    ap.add_argument("--listen", action="append", required=True, help="puerto=host:puerto_destino")
    args = ap.parse_args()
    for spec in args.listen:
        port, target = spec.split("=")
        host, tport = target.rsplit(":", 1)
        STATE[int(port)] = {"mode": "pass", "latency_ms": 0, "target": (host, int(tport)), "conns": []}
        threading.Thread(target=_listen, args=(int(port),), daemon=True).start()
        print(f"proxy :{port} -> {host}:{tport}", flush=True)
    print(f"admin en :{args.admin}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.admin), Admin).serve_forever()  # nosec B104
