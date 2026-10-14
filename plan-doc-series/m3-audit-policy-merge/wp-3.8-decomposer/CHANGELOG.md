# WP-3.8 — Decomposer support (backend permission half)

## Unreleased

### Done — MT-3.8-01 (backend decomposer permission, draft-only)

- The Section 12.2 **Decomposer column is now enforced on the real
  route**: `POST /api/v1/projects/{pid}/tasks` answers the actual
  matrix row class `CanCreateDraftTasks` (owner, `decomposer` agent
  role, device — the class WP-1.2/1.4 already carried with its
  recorded Device "Yes (Could)" grant), swapped in via
  `TaskListCreateView.get_permissions()` for the POST method only —
  the GET half stays Section 9.2's Owner caller, and the write half
  is the matrix row (UC-10; G-19).
- The role identity is the **agent token's `scopes`** — the same
  identification mechanism as coder/auditor (Section 10.5 role
  plumbing): an owner-minted project-scoped token with the
  `decomposer` scope. No free-text request field is trusted
  (MT-3.8-01 risk note): a coder-scoped token cannot widen itself to
  draft creation, and the decomposer cannot widen itself to any other
  project (ADR-004 zero-bleed asserted both ways).
- A decomposer causes **T1 only**: created tasks land in `draft`
  with the server-allocated `{PID}-T{index}` id and the
  `task.created` event (Section 8.2). Every Section 12.2 "No" cell
  with a live endpoint answers `ROLE_NOT_PERMITTED` for the
  decomposer token — claim `pending` (T4), claim `to_be_audited`
  (T11), submit resolution (T7), submit verdict, review decisions
  (`POST /tasks/{id}/review`, WP-3.6), and PATCH task details;
  publish/unpublish and the merge queue keep their matrix probe
  cells (`test_authorization_matrix.py` — their routes land with the
  remaining WP wiring). Owner/coder/auditor create answers are
  unchanged (regressions asserted).
- **Matrix activation (the sanctioned path).** The MT-1.4-03
  deferred-cells note prescribed exactly this activation: "swapping
  the view's permission class to `CanCreateDraftTasks` … and
  flipping these rows to allowed". Both formerly-deferred
  "Create draft tasks" cells (Decomposer and Device — the latter's
  grant rides the same class) are now walked as allowed on the real
  route in `test_authorization_matrix.py`; `DEFERRED_MATRIX_CELLS`
  is empty, its recorded-and-still-denied mechanism intact for the
  next deferred cell. The cross-project acceptance sharpened: the
  same decomposer token creates on its own project (201) and is
  refused on a foreign one by **scope alone**.
- Tests: `tests/test_decomposer_permissions.py` (the named MT suite —
  one case per printed cell + regressions) and the matrix suite
  (22 cases) green; full backend suite green.

### Notes / out of scope (per the MT)

- MT-3.8-02's bridge tool (`create_draft_task` MCP schema + wiring)
  and MT-3.8-03's tool-level restriction suite are the bridge
  owner's; they call this route with a `decomposer`-scoped token and
  inherit this server-side boundary. The bridge catalog already
  carries `task_create_draft` (POST `/api/v1/projects/{pid}/tasks`)
  — no OpenAPI change was needed for the permission swap, so the
  byte-stable snapshot was regenerated once at convergence with no
  diff from this MT.
- Device create-draft stays the recorded WP-1.4 "Yes (Could)" grant
  (not part of the decomposer role; §12.2 marks it Could).

## 2026-10-14 — Bridge half: MT-3.8-02 (create_draft_task tool)

### Delivered

`tools/schemas.py` registers `create_draft_task` with exactly the
Section 10.5 inputs — `title` (required), `description`, `criteria`,
`scope`, `test_command`, `priority`, `depends_on` — and nothing
else: **no project id** (bound-session rule, Section 10.5 tool
design) and **no state argument** (the created task is always
`draft`; T1 is the only transition the tool can cause — Section
8.2). The strict top-level schema (`additionalProperties: false`)
keeps the no-smuggling property shared by every bridge tool; a
client that passes `state:` gets `VALIDATION_ERROR`, never a
publish path. Catalog placement follows Section 10.5's order
(between `submit_audit_verdict` and `get_project_context`); pins
updated in `test_tool_schemas.py` and `test_layout.py`.

`tools/create_draft_task.py` forwards to the existing
task-creation endpoint (`task_create_draft` → `POST
/api/v1/projects/{pid}/tasks` — WP-1.4's service, Section 7.3 id
sequence under the project row lock; no parallel creation path).
Wire mapping per Section 7.2: `criteria` → `acceptance_criteria`,
`scope` → `target_scope`; every other field passes by its own
name. `depends_on` is forwarded only when supplied (omitted ≠
empty list). No session/lease fencing pair — creation is not a
lease operation; `Idempotency-Key` rides the transport (NFR-12,
ADR-012). The response echoes `task_id`, `state`, `priority`,
`depends_on`, `version` and a `next_action` (Section 10.5 design
rules). Errors are catalog-only: `ROLE_NOT_PERMITTED` (the MT-
3.8-01 boundary above), `VALIDATION_ERROR` (unknown/foreign/self/
cyclic `depends_on`, rolled back whole), malformed responses →
`SERVER_ERROR`.

### Concurrency protocol (MT-3.8-01 dependency, resolved)

Per the bridge/backend assignment protocol, the unit/contract
tests were first written against the documented contract via the
conftest `FakeBackend` stub plus ONE integration-marked test
documenting the real-backend expectation. MT-3.8-01 has since
landed (the permission half above), so the integration test now
**runs live** and was executed green on 2026-10-14:

```text
ORCHESTRATOR_BRIDGE_LIVE_TESTS=1 docker start wp16-pg &&
uv run --directory bridge pytest tests/test_create_draft_task.py -q -m integration
# 1 passed (14s): decomposer token creates draft parent + child
# (depends_on persisted), unknown dependency -> VALIDATION_ERROR,
# coder token -> ROLE_NOT_PERMITTED
```

The live seed (`tests/_live_backend.py`) now mints one
`decomposer`-scoped token alongside the five coder/auditor ones
for this proof. Without the opt-in flag the test skips with the
exact run command in the reason — the default suite stays green
without the stack.

Tests (`tests/test_create_draft_task.py`, 12 offline + 1 live):
catalog order, schema shape (no state / no project id), wire
contract (field-for-field body, Idempotency-Key present),
omitted-optionals defaults, empty-`depends_on` distinction,
role-denial translation, unknown-dependency translation,
malformed-response `SERVER_ERROR`, `tools/call` round-trip,
smuggled-`state` rejection, plus the live end-to-end above.

### Deferred

* **MT-3.8-03 (decomposer restriction tests)** — deferred per the
  assignment: the Section 12.2 "No"-cell restriction suite needs
  both MT-3.8-01 (landed) and MT-3.8-02 (this entry) fully merged
  and re-based on the final backend surface; the positive-control
  half (create succeeds, row is `draft`) is already covered by the
  live test above. Re-assign for the denial suite: publish,
  unpublish, claim `pending`/`to_be_audited`, resolution, verdict,
  review decisions, merge queue — backend half to the backend
  agent, tool-path half to the bridge owner.

### Files (bridge half)

`bridge/src/orchestrator_bridge/tools/create_draft_task.py`
(new), `tools/schemas.py`, `tools/registration.py`;
`bridge/tests/test_create_draft_task.py` (new),
`bridge/tests/_live_backend.py` (decomposer token seed);
pinned-test updates (`test_tool_schemas.py`, `test_layout.py`);
`bridge/pyproject.toml` (integration marker).
