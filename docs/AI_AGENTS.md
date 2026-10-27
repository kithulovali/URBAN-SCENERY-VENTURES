# Integrated AI agents

Three endpoints are registered under the existing API v1 prefix:

- `POST /api/v1/ai/agents/business-intelligence`
- `POST /api/v1/ai/agents/product-discovery`
- `POST /api/v1/ai/agents/marketing-content`

Request body: `{"question":"Identify low-stock products and suggest priorities."}`

The agents read the existing `products` and `orders` tables. Context is capped at 300 products and 1,000 orders per request, so metrics are not guaranteed lifetime totals. Agents do not write to the database or publish social posts.

Gemini is used when `GOOGLE_API_KEY` or `GEMINI_API_KEY` is configured. Optionally set `GEMINI_MODEL` (default `gemini-2.5-flash`). Install the SDK with `pip install google-genai`; store the API key in the local environment or deployment secret manager and do not commit it. Without a key, deterministic fallback responses support local smoke testing.

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ai/agents/business-intelligence \
  -H 'Content-Type: application/json' \
  -d '{"question":"Identify low-stock products and suggest priorities."}'
```
