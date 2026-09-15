#!/bin/bash
cd "$(dirname "$0")"
# API key resolution: explicit env var wins, else macOS Keychain (one-time setup:
#   security add-generic-password -a "$USER" -s 'prompt-compiler-gemini' -w
# ), else fall back to local Ollama.
if [ -z "$GEMINI_API_KEY" ]; then
  GEMINI_API_KEY="$(security find-generic-password -s 'prompt-compiler-gemini' -w 2>/dev/null)"
  export GEMINI_API_KEY
fi
# Fix TLS certs for python.org macOS builds (needed for Gemini HTTPS calls)
CERT_FILE="$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)"
if [ -n "$CERT_FILE" ]; then
  export SSL_CERT_FILE="$CERT_FILE"
fi
if [ -z "$GEMINI_API_KEY" ]; then
  echo "No GEMINI_API_KEY — using local Ollama backend..."
  ollama serve &>/dev/null &
  sleep 2
else
  echo "Using Gemini backend (${GEMINI_MODEL:-gemini-2.5-flash})"
fi
echo "Starting proxy on http://localhost:8080 ..."
python3 proxy.py
