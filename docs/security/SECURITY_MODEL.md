# Mia Security Model

## Trust boundaries

Mia Core and the n8n Tool Gateway use separate shared secrets. Every `/mia/*`
route except explicit health checks requires `MIA_CORE_API_TOKEN`; the gateway
fails closed when `MIA_TOOL_GATEWAY_TOKEN` is missing. Rotate both values as
independent high-entropy secrets and do not expose either service directly.

The OpenCode gateway (`mia-opencode`) follows the same rule: it fails closed
when `MIA_CODE_GATEWAY_TOKEN` is unset, and compares the bearer token in
constant time. The n8n Tool Gateway also compares `x-mia-tool-token` in
constant time instead of `!==`.

## External writes

Calendar, Gmail, Drive, Docs, Sheets, Tasks, Automation, and GitHub mutations
require an exact positive confirmation. Negated or embedded phrases are not
accepted. A pending action is scoped to both chat and user, atomically claimed,
and expires after 15 minutes. A durable execution journal derives an idempotency
key from user, request, tool, and canonical arguments to prevent duplicate side
effects during retries.

**Code agent writes are covered by the same flow.** `code_apply_to_existing_project`,
`code_publish_project`, and `code_fix_from_issue` (with PR creation) create a
pending action instead of trusting a `confirmed` flag supplied by the model;
after the user confirms, the action dispatches to the OpenCode gateway through
`run_pending_action`. OpenCode's bash allowlist excludes `python`/`cat`/`tail`/
`sed`/`awk` prefixes so `.env` files cannot be trivially exfiltrated, and its
permission config denies reading or editing `.env` files.

## Memory and secret handling

- `memory.write` rejects content matching `SECRET_PATTERNS` (api keys, tokens,
  passwords, long random strings) — previously only memory proposals were
  filtered. Auto-written document/web context is now protected too.
- `Settings.validate()` refuses to start when `MIA_POSTGRES_URI` still contains
  the default `n8n_password`.

## Network and content controls

- Web fetch validates DNS before every request and redirect, rejects credentials
  in URLs and private/reserved addresses, and caps redirects and response bytes.
- The n8n Tool Gateway additionally rejects private/local URLs for
  `web.read_url` / `web.summarize_url` / `web.ask_url` (SSRF guard at the edge).
- Media inputs use strict base64 decoding, bounded input sizes, and sanitized names.
- MCP servers must use HTTPS and each callable tool must be explicitly allowlisted
  as read-only.
- Per-user/path sliding-window limits protect Mia Core endpoints.

## Operational recommendations

Put n8n and Mia Core on a private Docker network, bind host ports to loopback
(mia-core now binds `127.0.0.1:8000`), use least-privilege Google/GitHub
credentials, and review `/mia/ops/metrics` for failed executions, expired
approvals, and automation errors. Never commit `.env` or provider tokens.
