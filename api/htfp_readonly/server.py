"""Short-lived loopback HTTP transport using the standard library parser."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

from .core import Application


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(2)

    def parse_request(self):
        if not super().parse_request():
            return False
        # The stdlib accepts legacy GETs but suppresses all response headers for
        # HTTP/0.9. Reject that transport before any application data is read.
        if self.request_version == "HTTP/0.9":
            self.close_connection = True
            return False
        return True

    def do_GET(self):
        lengths = self.headers.get_all("Content-Length", [])
        no_body = (not self.headers.get_all("Transfer-Encoding", [])
                   and (not lengths or lengths == ["0"]))
        # The stdlib normalizes a leading '//'. Apply our origin-form policy to
        # its already parsed original target, without replacing HTTP parsing.
        original_target = self.requestline.split()[1]
        status, body = self.server.application.handle(original_target, body_supported=no_body)
        encoded = (json.dumps(body, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > 16384:
            raise RuntimeError("Fixed response exceeds application limit")
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        pass  # No user-supplied request/header echo or tracebacks in API responses.


def make_server(profile="unconfigured", port=0, handler_class=Handler):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer from0 to65535")
    application = Application(profile)
    server = HTTPServer(("127.0.0.1", port), handler_class)
    server.application = application
    return server
