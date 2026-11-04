"""The arena's world (skynetv2.md → D18), one per lane. The runner loads a suite's round into it on
:8081 (the runner alone, by name); the lane's agent calls it on :8080 under the suite's tool names
(this container's aliases on the lane's network). The suite's own world.py answers: load(round),
log() for the checks, and Handler for the agent's calls."""
import http.server
import importlib
import json
import socket
import sys
import threading

sys.path.insert(0, "/arena")
ACTIVE = {}


def from_runner(ip):
    try:
        return ip == "127.0.0.1" or ip in {x[4][0] for x in socket.getaddrinfo("arena", None)}
    except OSError:
        return False


def reply(h, status, body):
    data = json.dumps(body, ensure_ascii=False, default=str).encode()
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(data)))
    h.end_headers()
    h.wfile.write(data)


class Admin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            return reply(self, 200, {"ok": True})
        if not from_runner(self.client_address[0]):
            return reply(self, 403, {"error": "the runner's only"})
        if self.path == "/log":
            return reply(self, 200, ACTIVE["world"].log() if ACTIVE else None)
        reply(self, 404, {"error": "no such path"})

    def do_POST(self):
        if not from_runner(self.client_address[0]):
            return reply(self, 403, {"error": "the runner's only"})
        if self.path != "/load":
            return reply(self, 404, {"error": "no such path"})
        a = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        world = importlib.import_module(f"suites.{a['suite']}.world")
        world.load(a["round"])
        ACTIVE["world"] = world
        reply(self, 200, {"loaded": a["round"]})

    def log_message(self, fmt, *args):
        pass


class Agent(http.server.BaseHTTPRequestHandler):
    def go(self, method):
        if not ACTIVE:
            return reply(self, 503, {"error": "nothing loaded"})
        ACTIVE["world"].Handler.answer(self, method)

    def do_GET(self):
        self.go("GET")

    def do_POST(self):
        self.go("POST")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=http.server.ThreadingHTTPServer(("0.0.0.0", 8081), Admin).serve_forever, daemon=True).start()
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Agent).serve_forever()
