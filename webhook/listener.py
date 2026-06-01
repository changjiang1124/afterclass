#!/usr/bin/env python3
"""GitHub webhook listener for afterclass auto-deploy.

Listens on 127.0.0.1:9000, verifies the X-Hub-Signature-256 HMAC against
GITHUB_WEBHOOK_SECRET, and runs deploy.sh in the background when a push to
refs/heads/main is received.
"""
import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 9000
DEPLOY_SCRIPT = "/var/www/afterclass/deploy.sh"
DEPLOY_LOG = "/var/www/afterclass/logs/webhook-deploy.log"
TARGET_REF = "refs/heads/main"

SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("webhook")

_deploy_lock = threading.Lock()


def verify_signature(body: bytes, header: str) -> bool:
    if not SECRET:
        log.error("GITHUB_WEBHOOK_SECRET is not set")
        return False
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def run_deploy():
    if not _deploy_lock.acquire(blocking=False):
        log.warning("deploy already running; skipping this trigger")
        return
    try:
        os.makedirs(os.path.dirname(DEPLOY_LOG), exist_ok=True)
        with open(DEPLOY_LOG, "ab") as fp:
            fp.write(b"\n===== deploy started =====\n")
            fp.flush()
            rc = subprocess.call(
                ["/bin/bash", DEPLOY_SCRIPT],
                stdout=fp,
                stderr=subprocess.STDOUT,
                cwd="/var/www/afterclass",
            )
            fp.write(f"===== deploy finished (rc={rc}) =====\n".encode())
        log.info("deploy finished rc=%s", rc)
    finally:
        _deploy_lock.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send(self, code: int, msg: str):
        body = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/health"):
            self._send(200, "ok\n")
        else:
            self._send(404, "not found\n")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 10 * 1024 * 1024:
            self._send(400, "bad length\n")
            return
        body = self.rfile.read(length)

        sig = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(body, sig):
            log.warning("signature check failed from %s", self.address_string())
            self._send(401, "invalid signature\n")
            return

        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self._send(200, "pong\n")
            return
        if event != "push":
            self._send(202, f"ignored event {event}\n")
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send(400, "invalid json\n")
            return

        ref = payload.get("ref", "")
        if ref != TARGET_REF:
            log.info("ignoring push to %s", ref)
            self._send(202, f"ignored ref {ref}\n")
            return

        log.info(
            "accepted push by %s after %s",
            payload.get("pusher", {}).get("name", "?"),
            payload.get("after", "?")[:8],
        )
        threading.Thread(target=run_deploy, daemon=True).start()
        self._send(202, "deploy queued\n")


def main():
    if not SECRET:
        log.error("GITHUB_WEBHOOK_SECRET env var is required")
        sys.exit(1)
    srv = HTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    log.info("listening on %s:%s", LISTEN_HOST, LISTEN_PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


if __name__ == "__main__":
    main()
