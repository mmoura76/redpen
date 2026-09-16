import http.server
import json
import os
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Backend priority: Groq > xAI > Gemini > Ollama
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

XAI_API_KEY = os.environ.get("XAI_API_KEY", "").strip()
XAI_MODEL = os.environ.get("XAI_MODEL", "grok-2-latest").strip() or "grok-2-latest"
XAI_URL = "https://api.x.ai/v1/chat/completions"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def forward_ollama(body):
    req = urllib.request.Request(
        OLLAMA_URL + '/api/generate',
        data=body,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return 200, resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:300]
        return 502, json.dumps({"error": f"Ollama error {e.code}: {detail}"}).encode()
    except Exception as e:
        return 502, json.dumps({"error": f"Ollama unreachable: {e}"}).encode()


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


def forward_xai(payload):
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
        "model": XAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }
    if payload.get("response_format") == "json":
        req_body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        XAI_URL,
        data=json.dumps(req_body).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {XAI_API_KEY}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:500]
        return 502, json.dumps({"error": f"xAI error {e.code}: {detail}"}).encode()
    except Exception as e:
        return 502, json.dumps({"error": f"xAI unreachable: {e}"}).encode()
    text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not text:
        return 502, json.dumps({"error": "xAI returned no text"}).encode()
    return 200, json.dumps({"response": text}).encode()


def forward_gemini(payload):
    prompt = payload.get("prompt", "")
    system = payload.get("system", "")
    options = payload.get("options") or {}
    try:
        temperature = float(options.get("temperature", 0.1))
    except (TypeError, ValueError):
        temperature = 0.1
    generation_config = {"temperature": temperature}
    if payload.get("response_format") == "json":
        generation_config["responseMimeType"] = "application/json"
    parts = [{"text": prompt}]
    for img_b64 in payload.get("images") or []:
        parts.append({"inline_data": {"mime_type": payload.get("image_mime", "image/png"), "data": img_b64}})
    req_body = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }
    if system:
        req_body["system_instruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(
        GEMINI_URL,
        data=json.dumps(req_body).encode(),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:500]
        return 502, json.dumps({"error": f"Gemini error {e.code}: {detail}"}).encode()
    except Exception as e:
        return 502, json.dumps({"error": f"Gemini unreachable: {e}"}).encode()
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not text:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "empty response")
        return 502, json.dumps({"error": f"Gemini returned no text ({reason})"}).encode()
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
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            if GROQ_API_KEY:
                try:
                    payload = json.loads(body.decode())
                except Exception:
                    status, data = 400, json.dumps({"error": "Groq backend expected a JSON body"}).encode()
                else:
                    status, data = forward_groq(payload)
            elif XAI_API_KEY:
                try:
                    payload = json.loads(body.decode())
                except Exception:
                    status, data = 400, json.dumps({"error": "xAI backend expected a JSON body"}).encode()
                else:
                    status, data = forward_xai(payload)
            elif GEMINI_API_KEY:
                try:
                    payload = json.loads(body.decode())
                except Exception:
                    status, data = 400, json.dumps({"error": "Gemini backend expected a JSON body"}).encode()
                else:
                    status, data = forward_gemini(payload)
            else:
                status, data = forward_ollama(body)
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
            if GROQ_API_KEY:
                payload = {"backend": "groq", "model": GROQ_MODEL, "ready": True}
            elif XAI_API_KEY:
                payload = {"backend": "xai", "model": XAI_MODEL, "ready": True}
            elif GEMINI_API_KEY:
                payload = {"backend": "gemini", "model": GEMINI_MODEL, "ready": True}
            else:
                try:
                    with urllib.request.urlopen(OLLAMA_URL + '/api/tags', timeout=3) as r:
                        ready = r.status == 200
                except Exception:
                    ready = False
                payload = {"backend": "ollama", "model": "gemma3:4b", "ready": ready}
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
    if GROQ_API_KEY:
        backend = f"Groq ({GROQ_MODEL})"
    elif XAI_API_KEY:
        backend = f"xAI ({XAI_MODEL})"
    elif GEMINI_API_KEY:
        backend = f"Gemini ({GEMINI_MODEL})"
    else:
        backend = f"Ollama ({OLLAMA_URL})"
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Running at http://0.0.0.0:{PORT}")
    print(f"Backend: {backend}")
    server.serve_forever()
