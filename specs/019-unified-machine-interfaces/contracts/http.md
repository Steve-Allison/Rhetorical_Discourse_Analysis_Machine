# Contract: Optional Local HTTP

**Status**: Proposed Feature 019 transport, not implemented routes.

## Surface

One immutable Machine is constructed at server startup. Python and CLI do not
require the server or its optional dependencies. `rdam serve` requires `rdam[http]`;
missing dependencies produce a safe startup error, not an automatic installation.

| Method / route | Input | Success response |
|---|---|---|
| GET /v1/capabilities | None | Canonical MachineCapabilities |
| POST /v1/prepare | PreparationRequest | Canonical MachinePreparation |
| POST /v1/analyse | AggregateRequest | Canonical AggregateAnalysis v2 |
| POST /v1/view | ViewRequest | Canonical AnalysisView |
| POST /v1/summary | Supported persisted record accepted by summarise | UTF-8 plain-text summary plus LF |
| GET /v1/schemas/{record} | Optional mode=validation or serialization | Shared generated JSON Schema |
| GET /v1/version | None | Canonical VersionInfo |

Route version and record version are independent. No unversioned aliases, old
RST routes, per-request model configuration, job endpoints or result storage.
Unknown paths are 404; known paths with wrong methods are 405 with Allow.
Unknown/duplicate query parameters are 400. Schema mode defaults to validation;
other routes accept no query parameters. No trailing-slash redirects.

POST bodies are the exact shared records, not a text field containing JSON.
SourceArtifact raw bytes use the same base64 codec. Paths/URLs in provenance are
never dereferenced. No multipart upload, server filename input or remote fetch.
Request bodies and model responses are not written to transport logs.

## Representation and errors

Successful JSON uses `Content-Type: application/json`, exact shared serialized
UTF-8 bytes without a trailing LF, and a correct Content-Length. No second JSON
encoder, double serialization, compression or TTY-dependent representation.
Responses set `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.
The server sends no permissive CORS headers.

Every valid aggregate is HTTP 200, including partial/unsuccessful analysis. Its
own status distinguishes analytical completion. An empty valid finding is not
an HTTP error. A successfully selected view is 200 regardless of original status.

Application-generated failures use the shared OperationFailure JSON record:

| HTTP | Cause |
|---|---|
| 400 | Malformed JSON/encoding/base64, invalid request/config fields, conflicting headers, unsupported schema name/version, unknown query |
| 403 | Rejected Host or Origin |
| 404 / 405 | Unknown route / wrong method |
| 408 | Body-read deadline exceeded while response is still possible |
| 411 | Required Content-Length missing |
| 413 | Declared or received body exceeds the configured byte limit |
| 415 | Unsupported media or Content-Encoding |
| 422 | Source is decodable but semantic preparation fails |
| 503 | Admission busy or required optional preparation dependency unavailable |
| 500 | Unexpected internal defect; no invented partial aggregate |

Use safe catalogued codes/messages; no raw exception, source, prompt, key or
local path in diagnostic bodies. Provider-level failures remain in the aggregate.
The external HTTP parser may reject malformed protocol before ASGI receives it;
those parser responses are not guaranteed RDAM JSON. A disconnected peer cannot
be promised any response. Test these boundaries explicitly rather than claiming
universal JSON error delivery.

## Local safety and resource limits

`--host` accepts only `127.0.0.1` (default) or `::1`; no wildcard or arbitrary DNS
binding. `--port` is an integer 0..65535, default 8765. Port 0 reports the actual
bound port. Host validation accepts the bound address or localhost with that
exact port, using valid IPv6 bracket syntax where required. Reject other Host
values and duplicates. Local processes are trusted peers; no user/role/auth system.

Reject any Origin header on POST, including null and a purported localhost
origin. This is a non-browser local API. GET discovery remains model-free and
has no mutation. No proxy-header trust, reload, WebSocket or cross-origin feature.

POST requires exactly one valid nonnegative decimal Content-Length and JSON
media type, allowing only absent charset or utf-8. Reject Transfer-Encoding and
Content-Encoding other than identity. GET bodies are forbidden. Uvicorn/h11 owns
protocol parsing; the adapter validates the headers it receives before work.

Limits:

- `--max-request-bytes`: positive integer, default 67,108,864 bytes (64 MiB),
  applied to the whole encoded JSON body, including base64 overhead.
- `--body-timeout-seconds`: positive finite number, default 30, measured from
  completed headers to completed body, not reset indefinitely by small chunks.
- One admission slot shared by all POST operations, acquired before body loading;
  another POST receives 503 immediately, with no unbounded work queue.
- Uvicorn connection/task concurrency limit 32, h11 incomplete-event buffer
  16,384 bytes, keep-alive timeout 5 seconds. Parser/concurrency rejections may
  precede RDAM JSON handling. These are connection/buffer limits, not a claim of
  a separate total header-read deadline.

Byte limits do not replace existing archive-expansion/source-validation limits.
Responses are complete records; there is no silent truncation to satisfy a size
budget. Increasing the explicit request limit is a local resource choice.

## Execution and lifecycle

Use Starlette with raw-byte Response objects and Uvicorn in one process, asyncio
and h11. Run blocking Machine calls off the event loop. GET discovery remains
responsive while an admitted analysis runs; GET never constructs another model.
Disable access logging and configure safe lifecycle/error messages only.

A body timeout is not an inference timeout. Preserve provider retry/deadline
settings and add no automatic retries. Client disconnect or Ctrl-C cannot forcibly
stop already-running Python inference threads: cancel work not started, keep the
admission slot until running work ends, then release it. Drain during orderly
shutdown; do not admit a second run because the first caller disconnected.
No background job/result retrieval is implied by work finishing after disconnect.

`serve` writes a safe JSON listening event to stderr with event="listening" and
the actual loopback URL, after successful binding. Stdout stays empty. Startup
configuration errors and port conflicts exit nonzero with a safe diagnostic.

## Parity

Python, CLI and HTTP use identical decoded requests, effective configuration,
native validators, guide binding and serializer. Identical deterministic inputs
produce equal canonical records; CLI's single LF is the only framing difference.
Model-backed comparisons use the same external response fixture and declared
native execution-field normalization, never blanket deletion of differing keys.
