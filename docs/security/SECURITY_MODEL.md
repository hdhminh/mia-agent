# Mia Security Model

## Trust boundaries

Mia Core and the n8n Tool Gateway use separate shared secrets. Every `/mia/*`
route except explicit health checks requires `MIA_CORE_API_TOKEN`; the gateway
fails closed when `MIA_TOOL_GATEWAY_TOKEN` is missing. Rotate both values as
independent high-entropy secrets and do not expose either service directly.

## External writes

Calendar, Gmail, Drive, Docs, Sheets, Tasks, Automation, and GitHub mutations
require an exact positive confirmation. Negated or embedded phrases are not
accepted. A pending action is scoped to both chat and user, atomically claimed,
and expires after 15 minutes. A durable execution journal derives an idempotency
key from user, request, tool, and canonical arguments to prevent duplicate side
effects during retries.

## Network and content controls

- Web fetch validates DNS before every request and redirect, rejects credentials
  in URLs and private/reserved addresses, and caps redirects and response bytes.
- Media inputs use strict base64 decoding, bounded input sizes, and sanitized names.
- MCP servers must use HTTPS and each callable tool must be explicitly allowlisted
  as read-only.
- Per-user/path sliding-window limits protect Mia Core endpoints.

## Operational recommendations

Put n8n and Mia Core on a private Docker network, bind host ports to loopback,
use least-privilege Google/GitHub credentials, and review `/mia/ops/metrics` for
failed executions, expired approvals, and automation errors. Never commit `.env`
or provider tokens.
