#!/bin/bash
cd "$(dirname "$0")"
# Single backend: Groq. Export your key before running:
#   export GROQ_API_KEY="gsk_..."
if [ -z "$GROQ_API_KEY" ]; then
  echo "ERROR: GROQ_API_KEY is not set."
  echo "Run: export GROQ_API_KEY=\"gsk_...\" && ./start.sh"
  exit 1
fi
# Fix TLS certs for python.org macOS builds (needed for Groq HTTPS calls)
CERT_FILE="$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)"
if [ -n "$CERT_FILE" ]; then
  export SSL_CERT_FILE="$CERT_FILE"
fi
echo "Using Groq backend (${GROQ_MODEL:-openai/gpt-oss-20b})"
if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "No OPENROUTER_API_KEY — running without fallback. (Optional: export OPENROUTER_API_KEY for automatic failover.)"
else
  echo "Fallback: OpenRouter (${OPENROUTER_MODEL:-openrouter/free})"
fi
echo "Starting proxy on http://localhost:8080 ..."
python3 proxy.py
