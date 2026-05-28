"""
health_server.py - Servidor HTTP mínimo para Render
Render requiere un puerto HTTP activo para no matar el proceso.
UptimeRobot hace ping cada 10 min para evitar que duerma.
"""

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            body = (
                f"🤖 Crypto Scalping Bot — ACTIVO\n"
                f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"✅ OK"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silenciar logs de cada ping


def start_health_server():
    """Arrancar el servidor de salud en un hilo separado"""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"✅ Health server corriendo en puerto {port}")
    return server
