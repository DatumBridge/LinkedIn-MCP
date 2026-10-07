# create_post

Create a personal LinkedIn feed post (text and/or article URL). Requires confirm=true.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `text` | no | Post commentary text (required unless article_url is set) |
| `visibility` | no | Visibility: PUBLIC or CONNECTIONS (default CONNECTIONS) |
| `article_url` | no | Optional https article URL to share |
| `article_title` | no | Optional title for article share |
| `article_description` | no | Optional description for article share |
| `author_urn` | no | Optional urn:li:person:... (must match authenticated member) |
| `confirm` | no | Must be true to publish (side effect). Use dry_run to preview. |
| `dry_run` | no | If true, return the request payload without calling LinkedIn |

## Cases

### Typical call

Input:

```json
{
  "text": "hello",
  "dry_run": true
}
```

Output:

```json
{
  "success": true,
  "post_id": "example-id",
  "post_urn": "example",
  "author_urn": "example",
  "visibility": "example",
  "message": "example",
  "dry_run": false,
  "request_body": "example"
}
```

### Preview the write

Set `dry_run` to true. The tool returns the planned change and does not send it.

Input:

```json
{
  "text": "hello",
  "dry_run": true
}
```

### Confirmed write

Set `confirm` to true. Omit `dry_run`.

Input:

```json
{
  "text": "hello",
  "confirm": true
}
```

### Write without confirm or dry_run

Input:

```json
{
  "text": "hello"
}
```

Output:

```json
{
  "success": false,
  "error_message": "confirm=true required for write tools (or dry_run=true to preview)"
}
```
