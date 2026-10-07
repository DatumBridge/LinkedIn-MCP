# get_post

Fetch a LinkedIn UGC post by URN (untrusted external content).

The gateway injects `credentials_json` from the connected account. Do not invent a token or paste a secret into the arguments.

## Parameters

| Name | Required | Meaning |
|---|---|---|
| `post_urn` | yes | UGC post URN (urn:li:ugcPost:... or urn:li:share:...) |

## Cases

### Typical call

Input:

```json
{
  "post_urn": "example"
}
```

Output:

```json
{
  "success": true,
  "post": "example"
}
```

### Missing `post_urn`

The tool rejects the call and does not guess the missing value.

Input:

```json
{}
```

Output:

```json
{
  "success": false,
  "error": {
    "error_code": "invalid_argument",
    "error_message": "post_urn is required",
    "retryable": false
  }
}
```
