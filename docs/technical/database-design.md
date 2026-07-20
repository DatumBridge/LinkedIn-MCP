# Database Design — LinkedIn MCP

No database in v1.

- OAuth pending state is in-memory with TTL (local UI only).
- Durable tokens are caller-owned (`credentials_json` / `token.json`).
- No Mongo/Redis/Postgres dependency.
