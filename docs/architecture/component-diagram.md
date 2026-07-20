# Component Diagram — LinkedIn MCP

```text
┌─────────────────┐     Streamable HTTP      ┌──────────────────┐
│ Studio / Agent  │ ───────────────────────► │ FastMCP tools    │
└─────────────────┘                          │  get_me          │
                                             │  create_post     │
                                             │  create_image…   │
                                             │  get/delete_post │
                                             └────────┬─────────┘
                                                      │
                                             ┌────────▼─────────┐
                                             │ LinkedInService  │
                                             └────────┬─────────┘
                                                      │ HTTPS
                                             ┌────────▼─────────┐
                                             │ api.linkedin.com │
                                             └──────────────────┘
```

OAuth connect (local only): browser → `/oauth/start` → LinkedIn → `/oauth/callback` → redeem `/oauth/token`.
