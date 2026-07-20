# ADR-0002 — LinkedIn OAuth scopes (Consumer tier)

## Context

LinkedIn products split Consumer (Sign In + Share) from Marketing/Community Management (partner-gated).

## Decision

Default OAuth scopes for v1:

```text
openid profile email w_member_social
```

Use OpenID `userinfo` for identity and `POST /v2/ugcPosts` for member shares.

## Alternatives Considered

- Community Management / Posts API with org scopes — deferred (partner access + higher blast radius).
- Legacy `r_liteprofile` / `r_emailaddress` — rejected (deprecated in favor of OIDC).

## Consequences

- Org page tools are non-goals until a separate scope ADR.
- Apps must enable Sign In (OIDC) + Share on LinkedIn products.

## Trade-offs

Shippable self-serve API surface vs fewer social-graph features.

## Risks

Share product not approved on the app → create tools fail with permission errors (fail-fast, documented).
