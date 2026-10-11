"""M0 placeholder backend (WP-0.2).

One stub image serves the four Section 16.1 backend-image roles so the Compose
stack can prove service topology, dependency ordering and health checks before
the real Django/Celery images arrive (WP-1.1):

  serve   -> ASGI stand-in: HTTP 200 on every path, including /health/ready
  worker  -> Celery-worker stand-in: answers the worker ping on :8001/ping
  beat    -> Celery-beat stand-in: scheduler loop as PID 1 (process check)
  migrate -> one-shot: exits 0 (the Section 16.1 "exit code" health check)

WP-1.1 replaces this image with the real backend; service names, ports and
health-check paths in compose.yaml stay unchanged (MT-0.2-01/04 risk notes).
"""

from __future__ import annotations

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVICE_MODE = sys.argv[1] if len(sys.argv) > 1 else "serve"

READY_BODY = b"ok\n"


class _Handler(BaseHTTPRequestHandler):
    """Answers every request with 200 (health endpoints included)."""

    server_version = "backend-stub"

    def _respond(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(READY_BODY)))
        self.end_headers()
        self.wfile.write(READY_BODY)

    do_GET = _respond
    do_POST = _respond

    def log_message(self, *_args: object) -> None:
        pass  # keep container logs quiet


def main() -> None:
    if SERVICE_MODE == "migrate":
        print("stub migrate: no-op until WP-1.1 ships real migrations", flush=True)
        return
    if SERVICE_MODE == "beat":
        print("stub beat: scheduler loop started", flush=True)
        while True:
            time.sleep(30)
    port = 8000 if SERVICE_MODE == "serve" else 8001
    label = "stub %s listening on :%d" % (SERVICE_MODE, port)
    print(label, flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), _Handler).serve_forever()


if __name__ == "__main__":
    main()
