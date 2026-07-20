# ADR-0001 — Tool-server, not relay

## Context

DatumBridge MCP services are either Python FastMCP tool-servers or Go WS relays.

## Decision

Implement LinkedIn as a **Python FastMCP tool-server** under `mcp/linkedin-mcp`.

## Alternatives Considered

- Extend `social-listening` with LinkedIn Apify actors — rejected (scraping/ToS risk; different product).
- Build a WS hub relay — rejected (no edge device hop).

## Consequences

- Follow `TEMPLATE_PYTHON_TOOL_SERVER.md` and gmail-mcp patterns.
- No pairing, device registry, or edge catalog.

## Trade-offs

Faster ship and clearer security boundary vs no offline/edge LinkedIn agent.

## Risks

Mis-copying hub patterns; mitigated by explicit non-goals in `design.md`.
