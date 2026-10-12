curl -s -X POST http://localhost:8000/validate -H "Content-Type: application/json" -d @payload.json | python3 -m json.tool
