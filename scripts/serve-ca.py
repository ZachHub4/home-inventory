"""Serve ONLY the CA certificate over plain HTTP, so a phone can install it.

Run this once during setup, install the certificate on the phone, then stop it
with Ctrl+C. Everything else is served over HTTPS by app.py.

    python scripts/serve-ca.py

Deliberately serves a single file. Never point a directory server at certs/ -
that folder holds private keys.
"""

import http.server
import socket
from pathlib import Path

PORT = 8000
CA_PATH = Path(__file__).parent.parent / "certs" / "ca-cert.crt"


class CertOnlyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/ca-cert.crt"):
            self.send_error(404, "Only /ca-cert.crt is available here")
            return

        data = CA_PATH.read_bytes()
        self.send_response(200)
        # This content type makes iOS offer to install it as a profile.
        self.send_header("Content-Type", "application/x-x509-ca-cert")
        self.send_header("Content-Disposition", 'attachment; filename="ca-cert.crt"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} -> {fmt % args}")


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    if not CA_PATH.exists():
        raise SystemExit(f"No CA certificate at {CA_PATH}. Run scripts/make-certs.sh first.")

    ip = local_ip()
    print("Serving the CA certificate (and nothing else).")
    print(f"\n  On your phone, open:  http://{ip}:{PORT}/ca-cert.crt\n")
    print("Press Ctrl+C when the certificate is installed.")

    http.server.HTTPServer(("0.0.0.0", PORT), CertOnlyHandler).serve_forever()
