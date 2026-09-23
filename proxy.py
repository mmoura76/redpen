import http.server
import json
import os
import urllib.request
import urllib.error

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Single backend: Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def forward_groq(payload):
    prompt = payload.get("prompt", "")
    system = payload.get("system", "")
    options = payload.get("options") or {}
    try:
        temperature = float(options.get("temperature", 0.1))
    except (TypeError, ValueError):
        temperature = 0.1
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    req_body = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }
    if payload.get("response_format") == "json":
        req_body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(req_body).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {GROQ_API_KEY}', 'User-Agent': 'RedPen/1.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:500]
        return 502, json.dumps({"error": f"Groq error {e.code}: {detail}"}).encode()
    except Exception as e:
        return 502, json.dumps({"error": f"Groq unreachable: {e}"}).encode()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not text:
        return 502, json.dumps({"error": "Groq returned no text"}).encode()
    return 200, json.dumps({"response": text}).encode()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path.split('?')[0] == '/api/generate':
            if not GROQ_API_KEY:
                status, data = 502, json.dumps({"error": "GROQ_API_KEY is not set on the server"}).encode()
            else:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                try:
                    payload = json.loads(body.decode())
                except Exception:
                    status, data = 400, json.dumps({"error": "Groq backend expected a JSON body"}).encode()
                else:
                    status, data = forward_groq(payload)
            self.send_response(status)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        route = self.path.split('?')[0]
        if route in ('/', '/index.html'):
            try:
                with open(os.path.join(BASE_DIR, 'index.html'), 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'text/html')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
        elif route == '/proxy':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'OK')
        elif route == '/api/health':
            payload = {"backend": "groq", "model": GROQ_MODEL, "ready": bool(GROQ_API_KEY)}
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Running at http://0.0.0.0:{PORT}")
    if GROQ_API_KEY:
        print(f"Backend: Groq ({GROQ_MODEL})")
    else:
        print("WARNING: GROQ_API_KEY is not set — /api/generate will return an error.")
    server.serve_forever()
