#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

if [ -z "$AZURE_CU_KEY" ]; then
  echo "ERROR: AZURE_CU_KEY non definita. Imposta la variabile o crea un file .env" >&2
  exit 1
fi

ENDPOINT="https://contentunderstandingipl.services.ai.azure.com"
API_KEY="$AZURE_CU_KEY"
FILE_PATH="${1}"
ANALYZER_ID="${2}"
API_VERSION="2025-11-01"

if [ -z "$FILE_PATH" ] || [ -z "$ANALYZER_ID" ]; then
  echo "Uso: $0 <percorso-pdf> <analyzer-id>" >&2
  exit 1
fi

if [ ! -f "$FILE_PATH" ]; then
  echo "ERROR: file non trovato: $FILE_PATH" >&2
  exit 1
fi

FILE_NAME=$(basename "$FILE_PATH")
MIME_TYPE="application/pdf"
TMP_JSON=$(mktemp /tmp/cu_payload_XXXXXX.json)

python3 -c "
import base64, json, sys
with open('$FILE_PATH', 'rb') as f:
    data = base64.b64encode(f.read()).decode()
payload = {'inputs': [{'name': '$FILE_NAME', 'mimeType': '$MIME_TYPE', 'data': data}]}
json.dump(payload, sys.stdout)
" > "$TMP_JSON"

echo "=== POST ==="
POST_RESPONSE=$(curl -i -s -X POST \
  "${ENDPOINT}/contentunderstanding/analyzers/${ANALYZER_ID}:analyze?api-version=${API_VERSION}" \
  -H "Ocp-Apim-Subscription-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  --data @"$TMP_JSON")

echo "$POST_RESPONSE"

RESULT_ID=$(echo "$POST_RESPONSE" \
  | grep -i "^operation-location:" \
  | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

rm -f "$TMP_JSON"

if [ -z "$RESULT_ID" ]; then
  echo "ERROR: impossibile estrarre RESULT_ID dall'header operation-location" >&2
  exit 1
fi

echo ""
echo ">>> RESULT_ID: $RESULT_ID"
echo ""
echo "=== GET (polling fino a Succeeded) ==="

GET_URL="${ENDPOINT}/contentunderstanding/analyzerResults/${RESULT_ID}?api-version=${API_VERSION}"
MAX_ATTEMPTS=20
INTERVAL=5

for i in $(seq 1 $MAX_ATTEMPTS); do
  echo "[tentativo $i/$MAX_ATTEMPTS]"
  GET_RESPONSE=$(curl -s -X GET \
    "$GET_URL" \
    -H "Ocp-Apim-Subscription-Key: ${API_KEY}")

  STATUS=$(echo "$GET_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
  echo "status: $STATUS"

  if [ "$STATUS" = "Succeeded" ] || [ "$STATUS" = "Failed" ]; then
    echo ""
    OUTPUT=$(echo "$GET_RESPONSE" | jq '{schema_label: .result.analyzerId, transform_di: true, data: .result.contents[0].fields}')
    echo "$OUTPUT"
    echo "$OUTPUT" > "./payload.json"
    echo ">>> Risultato salvato in payload.json"
    break
  fi

  if [ "$i" -eq "$MAX_ATTEMPTS" ]; then
    echo "Timeout: analisi non completata dopo $((MAX_ATTEMPTS * INTERVAL)) secondi" >&2
    exit 1
  fi

  sleep $INTERVAL
done
