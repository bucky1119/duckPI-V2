"""Loopback-only stateless review server; uploaded tables stay in memory."""
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .core import analyze, read_table, render_html

MAX_BODY = 100 * 1024 * 1024


def make_handler(initial=None):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json; charset=utf-8'):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def valid_request(self):
            expected = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected:
                self.send(403, json.dumps({'error': 'Use the printed 127.0.0.1 URL.'}))
                return False
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{expected}':
                self.send(403, json.dumps({'error': 'Cross-origin requests are not allowed.'}))
                return False
            return True

        def do_GET(self):
            if not self.valid_request():
                return
            if urlparse(self.path).path != '/':
                self.send(404, json.dumps({'error': 'Not found'}))
                return
            self.send(200, render_html(initial), 'text/html; charset=utf-8')

        def do_POST(self):
            if not self.valid_request():
                return
            if self.path != '/api/analyze':
                self.send(404, json.dumps({'error': 'Not found'}))
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= MAX_BODY:
                    self.send(413, json.dumps({'error': 'Request size must be 1 byte to 100 MiB.'}))
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('Request must be a JSON object.')
                for field in ['pairs', 'metadata']:
                    if not isinstance(payload.get(field), str):
                        raise ValueError(f'{field} must contain CSV/TSV text.')
                recorded = payload.get('recorded')
                if recorded is not None and not isinstance(recorded, str):
                    raise ValueError('recorded must contain CSV/TSV text.')
                report = analyze(read_table(io.StringIO(payload['pairs'])),
                                 read_table(io.StringIO(payload['metadata'])),
                                 method=payload.get('method', 'KING'),
                                 recorded=read_table(io.StringIO(recorded)) if recorded else None,
                                 relation_column=payload.get('relationColumn') or None)
                self.send(200, json.dumps(report, ensure_ascii=False, allow_nan=False))
            except (ValueError, KeyError, TypeError, UnicodeError) as e:
                self.send(400, json.dumps({'error': str(e)}))
    return Handler


def serve(port=8765, initial=None):
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(initial))
    print(f'duckPI review: http://127.0.0.1:{server.server_port}/ (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
