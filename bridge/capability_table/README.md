# Client capability table

`clients.json` is the **editable lookup table** the bridge's attachment tool
reads at resolution step 3 (parent plan Sections 10.4 step 3 and 10.9;
MT-2.5-02; ADR-006). Editing it needs no bridge release: change the file and
restart the bridge process (the table is loaded once per process, cached by
path).

## What a lookup does

Every `read_task_attachment` call resolves the session's image capability in
this order:

1. explicit `format_preference` in the call (except `auto`) — wins;
2. session capability from startup config (`ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY`);
3. **this file** — the MCP handshake client's `clientInfo.name` (and
   optional version window) matched case-insensitively, first match wins;
4. text-safe default `unknown` (OCR text + description, with a note on how
   to request the image explicitly).

`unknown` is treated as text-safe. Nothing here may make the bridge claim
vision the client did not prove (ADR-006; WP-5 exit criteria).

## Entry shape

```json
{
  "client_names": ["some-client"],
  "min_version": null,
  "max_version": null,
  "capability": "unknown",
  "source": "how this capability was verified",
  "notes": "context for future maintainers"
}
```

* `client_names` — one or more handshake names to match (lower-cased at
  load). Record the **observed** `clientInfo.name` from the initialize
  request, not a marketing name.
* `min_version` / `max_version` — optional dotted-version window
  (`"1.2.0"`); `null` matches any version. A caller whose version cannot be
  compared only matches entries with no bounds.
* `capability` — exactly one of `vision`, `text_only`, `unknown`; anything
  else is recorded as `unknown` with a warning.
* `source` — where the verification came from (required for review).
* `notes` — free text.

## Editing procedure (WP-2.11 conformance runs)

1. Run the client against the bridge and capture the initialize handshake's
   `clientInfo` name and version (never record tokens or secrets).
2. Drive one real image attachment through `read_task_attachment` with
   `format_preference="image_base64"`:
   * the image block renders — record `capability: "vision"`;
   * the client shows no image support / errors — record `capability:
     "text_only"` only if that is clearly the client's behavior;
   * anything ambiguous — leave `capability: "unknown"`.
3. Fill `source` (run date, client version, what was observed) and `notes`.
4. Commit the file change; no code release is required.

## Failure posture

A missing, unreadable or malformed file degrades to an **empty table**: every
client resolves `unknown` (text-safe) and a warning is logged — the bridge
never crashes and never guesses. Malformed entries are skipped one by one.

`ORCHESTRATOR_BRIDGE_CAPABILITY_TABLE` may point at an alternate file path
(useful for deployments that manage the table outside the repo).
