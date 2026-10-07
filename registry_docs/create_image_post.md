# create_image_post

Create a personal LinkedIn feed post with an image. Requires confirm=true.

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `image_base64` | yes | Image bytes encoded as base64 (size gated by LINKEDIN_MAX_IMAGE_BYTES) |
| `text` | no | Post commentary text |
| `image_media_type` | no | MIME type: image/jpeg, image/png, image/gif, or image/webp |
| `visibility` | no | Visibility: PUBLIC or CONNECTIONS (default CONNECTIONS) |
| `author_urn` | no | Optional urn:li:person:... (must match authenticated member) |
| `confirm` | no | Must be true to publish (side effect). Use dry_run to preview. |
| `dry_run` | no | If true, validate and return metadata without uploading/publishing |

## Cases

### Typical call

Input:

```json
{
  "image_base64": "example",
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

### Missing `image_base64`

The tool rejects the call and does not guess the missing value.

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
  "success": false,
  "error": {
    "error_code": "invalid_argument",
    "error_message": "image_base64 is required",
    "retryable": false
  }
}
```

### Preview the write

Set `dry_run` to true. The tool returns the planned change and does not send it.

Input:

```json
{
  "image_base64": "example",
  "text": "hello",
  "dry_run": true
}
```

### Confirmed write

Set `confirm` to true. Omit `dry_run`.

Input:

```json
{
  "image_base64": "example",
  "text": "hello",
  "confirm": true
}
```

### Write without confirm or dry_run

Input:

```json
{
  "image_base64": "example",
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
