# HelloSienna — Pre-M0 Implementation Contract

**Status:** Architecture v1 frozen. This document is the reviewable contract that must be approved before M0 implementation is authorized. It contains four deliverables and **no application code** (schema DDL and interface signature-stubs only, both of which are contracts, not implementations).

**Frozen invariant carried into everything below:** the UI never imports cognition code; all UI ↔ core traffic goes through the 127.0.0.1 API. Dependency direction is one-way: `shell → api → core → {persistence, providers}`; nothing points back up; `core/` imports nothing from `api/` or `shell/`.

> **Post-approval amendments (frozen, 2026-09-07).** Two changes were made after approval:
> - **Change 1 — token transport:** the per-launch token travels **only** as the `X-HS-Token` header, on every protected request including SSE (via authenticated streaming fetch, never native `EventSource`). The token must never appear in a URL/query string, a log line, persisted frontend state, or any repository file. See §3.6.
> - **Change 2 — soft-delete retrieval invariant:** a tombstoned memory (`deleted_at IS NOT NULL`) must never surface in cognition, retrieval, context construction, vector results, FTS results, or normal Sienna's Mind views — and correctness must not depend on callers remembering a filter. See §1.8.

---

## Deliverable 1 — Concrete SQLite Schema (M0–M5)

### 1.1 Conventions (apply to every table)

- **Primary keys:** `TEXT` UUID4-hex (`id`), generated in app code. *(Rationale + reversibility cost in §1.7.)* Tables keep their implicit `rowid` (no `WITHOUT ROWID`) so FTS5 external-content can reference it.
- **Timestamps:** `TEXT`, ISO-8601 **UTC** with `Z` suffix (e.g. `2026-09-07T09:00:00Z`), sortable lexicographically. Column suffix `_at`. Every value is produced by `Clock.now()` — never `datetime.now()`. Rendered to Asia/Kolkata only in the UI.
- **Enums:** `TEXT` + `CHECK (col IN (...))` (SQLite has no native enum).
- **Coarse magnitudes:** `importance`, `confidence` etc. are `LOW|MEDIUM|HIGH` text, never floats.
- **Connection PRAGMAs (mandatory, set per connection):** `PRAGMA foreign_keys=ON;` *(SQLite does NOT enforce FKs by default — this is a real footgun; enforce in both the app engine and Alembic's `env.py`)*, `PRAGMA journal_mode=WAL;` (lets background cognition read while foreground writes), `PRAGMA busy_timeout=5000;`.
- **Deletion:** domain records that appear in "Sienna's Mind" are **soft-deleted** via a `deleted_at` tombstone; a separate privacy "forget" path hard-deletes evidence and cascades. The tombstone invariant and how it is made hard to violate are defined in §1.8. Junction rows use `ON DELETE CASCADE`.

### 1.2 Migration → milestone mapping

| Migration | Lands at | Tables created |
|---|---|---|
| `0001_app_meta` | **M0** | `app_meta` only (proves the migration mechanism; no domain tables — see M0 non-goals) |
| `0002_conversation` | **M1** | `person`, `conversation`, `message`, `sienna_self` (+ seed USER/SIENNA/self rows) |
| `0003_memory` | **M2** | `evidence` (+immutability trigger), `memory` (+`memory_fts`+sync triggers), `memory_evidence`, `embedding` |
| `0004_attention` | **M3** | `event`, `open_thread` |
| `0005_boundary_checks` | **M5** | integrity views/pragmas only; **no new tables** |

**Deferred to their own milestone (do NOT create now):** `imported_dataset` + `evidence.imported_dataset_id` FK/CHECK (**M6**), `style_profile` (**M6/M7**), `belief` + `belief_evidence` (**M7**), `relationship_state` (**M7**), `tool_action` (**M8**). The `source_type` and `person.kind` enums already include the imported values, so no enum change is needed when imports arrive — only the `imported_dataset` table and one FK/CHECK.

### 1.3 DDL

```sql
-- ============ M0 ============
CREATE TABLE app_meta (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- ============ M1 ============
CREATE TABLE person (
  id           TEXT PRIMARY KEY,
  kind         TEXT NOT NULL CHECK (kind IN ('USER','SIENNA','IMPORTED_PERSON','OTHER')),
  display_name TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
-- seeded: exactly one ('USER'), exactly one ('SIENNA')

CREATE TABLE conversation (
  id         TEXT PRIMARY KEY,
  kind       TEXT NOT NULL CHECK (kind IN ('SIENNA','IMPORT')),
  title      TEXT,
  started_at TEXT NOT NULL
);

CREATE TABLE message (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
  sender          TEXT NOT NULL CHECK (sender IN ('USER','SIENNA','IMPORTED_PARTICIPANT')),
  text            TEXT NOT NULL,
  created_at      TEXT NOT NULL,   -- when stored (UTC)
  occurred_at     TEXT             -- original time for imported msgs (UTC); NULL for live
);
CREATE INDEX ix_message_conv ON message(conversation_id, created_at);

CREATE TABLE sienna_self (
  id                   INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton
  stable_identity_json TEXT NOT NULL,                       -- protected core facts
  evolving_traits_json TEXT NOT NULL DEFAULT '{}',
  style_profile_id     TEXT,                                -- (M6/M7) -> style_profile.id
  updated_at           TEXT NOT NULL
);

-- ============ M2 ============
CREATE TABLE evidence (
  id                  TEXT PRIMARY KEY,
  source_type         TEXT NOT NULL CHECK (source_type IN
                        ('IMPORTED_HISTORY','USER_STATED','SIENNA_EXPERIENCE',
                         'SIENNA_INFERENCE','DOCUMENT','TOOL_OBSERVATION')),
  timeline            TEXT NOT NULL CHECK (timeline IN ('INHERITED','SIENNA')),
  ref_kind            TEXT NOT NULL CHECK (ref_kind IN
                        ('MESSAGE','DOCUMENT','TOOL_ACTION','IMPORT','USER_INPUT')),
  ref_id              TEXT,                 -- soft polymorphic ref (no hard FK)
  text_snippet        TEXT NOT NULL,        -- self-contained snapshot of the source
  imported_dataset_id TEXT,                 -- (M6) NULL until imports exist
  occurred_at         TEXT,                 -- when the evidence content happened (UTC)
  created_at          TEXT NOT NULL,        -- when recorded (UTC)
  -- BOUNDARY INVARIANT (DB-enforced): timeline is a pure function of source_type
  CHECK (
    (source_type =  'IMPORTED_HISTORY' AND timeline = 'INHERITED') OR
    (source_type <> 'IMPORTED_HISTORY' AND timeline = 'SIENNA')
  )
);
CREATE INDEX ix_evidence_ref ON evidence(ref_kind, ref_id);

-- source_type / timeline are immutable after insert
CREATE TRIGGER evidence_provenance_immutable
BEFORE UPDATE OF source_type, timeline ON evidence
BEGIN
  SELECT RAISE(ABORT, 'evidence.source_type/timeline are immutable');
END;

CREATE TABLE memory (
  id                TEXT PRIMARY KEY,      -- rowid retained for FTS
  statement         TEXT NOT NULL,
  timeline          TEXT NOT NULL CHECK (timeline IN ('INHERITED','SIENNA')),
  subject_person_id TEXT REFERENCES person(id) ON DELETE SET NULL,
  importance        TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (importance IN ('LOW','MEDIUM','HIGH')),
  event_time        TEXT,                  -- optional temporal anchor (UTC)
  created_at        TEXT NOT NULL,
  deleted_at        TEXT                   -- soft-delete tombstone; NULL = active
);
CREATE INDEX ix_memory_live ON memory(timeline, importance) WHERE deleted_at IS NULL;

CREATE TABLE memory_evidence (
  memory_id   TEXT NOT NULL REFERENCES memory(id)   ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
  PRIMARY KEY (memory_id, evidence_id)
);
-- Cross-row rule "all evidence of a memory share the memory's timeline" is enforced
-- by the provenance guard (§3.5) at write time; §1.6 defines the audit query that
-- proves it in tests. (Cross-row invariants are deliberately NOT put in triggers.)

CREATE TABLE embedding (
  id         TEXT PRIMARY KEY,
  owner_type TEXT NOT NULL CHECK (owner_type IN ('MEMORY','EXAMPLE')),
  owner_id   TEXT NOT NULL,
  model      TEXT NOT NULL,
  dim        INTEGER NOT NULL,
  vector     BLOB NOT NULL,               -- float32 packed, byte-length = dim*4
  created_at TEXT NOT NULL,
  UNIQUE (owner_type, owner_id, model)
);
CREATE INDEX ix_embedding_owner ON embedding(owner_type, owner_id);

-- FTS5 lexical index over memory.statement (external-content, rowid-linked)
CREATE VIRTUAL TABLE memory_fts USING fts5(statement, content='memory', content_rowid='rowid');
CREATE TRIGGER memory_fts_ai AFTER INSERT ON memory BEGIN
  INSERT INTO memory_fts(rowid, statement) VALUES (new.rowid, new.statement);
END;
CREATE TRIGGER memory_fts_ad AFTER DELETE ON memory BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, statement) VALUES ('delete', old.rowid, old.statement);
END;
CREATE TRIGGER memory_fts_au AFTER UPDATE OF statement ON memory BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, statement) VALUES ('delete', old.rowid, old.statement);
  INSERT INTO memory_fts(rowid, statement) VALUES (new.rowid, new.statement);
END;
-- SOFT-DELETE (see §1.8): tombstoning is performed ONLY by MemoryRepository.soft_delete(),
-- which sets deleted_at AND deletes the row's memory_fts entry AND its embedding rows in one
-- transaction. So FTS and vector candidate sets physically cannot return a tombstoned memory;
-- the memory + memory_evidence rows are retained for provenance/audit and the hard-delete path.
-- (The AFTER UPDATE OF statement trigger above is unaffected — it fires only on statement edits.)

-- ============ M3 ============
CREATE TABLE event (
  id                 TEXT PRIMARY KEY,
  title              TEXT NOT NULL,
  event_time         TEXT,               -- UTC; NULL if only relative time known
  status             TEXT NOT NULL DEFAULT 'UPCOMING'
                       CHECK (status IN ('UPCOMING','PAST','UNKNOWN_OUTCOME')),
  importance         TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (importance IN ('LOW','MEDIUM','HIGH')),
  source_evidence_id TEXT REFERENCES evidence(id) ON DELETE SET NULL,
  created_at         TEXT NOT NULL
);
CREATE INDEX ix_event_time ON event(event_time, status);

CREATE TABLE open_thread (
  id                     TEXT PRIMARY KEY,
  topic                  TEXT NOT NULL,
  status                 TEXT NOT NULL DEFAULT 'OPEN'
                           CHECK (status IN ('OPEN','RESOLVED','DISMISSED','STALE')),
  importance             TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (importance IN ('LOW','MEDIUM','HIGH')),
  next_attention_at      TEXT,           -- UTC. DUE is DERIVED, never stored:
                                         -- due  <=>  status='OPEN' AND now >= next_attention_at
  expected_resolution_at TEXT,           -- UTC; past this w/o resolution -> STALE candidate
  linked_event_id        TEXT REFERENCES event(id) ON DELETE SET NULL,
  last_proactive_at      TEXT,           -- cooldown accounting
  created_at             TEXT NOT NULL,
  resolved_at            TEXT
);
CREATE INDEX ix_thread_due ON open_thread(status, next_attention_at);
```

### 1.4 Provenance & boundary enforcement (defense in depth)

Three layers guarantee *"`SIENNA_EXPERIENCE`/`SIENNA_INFERENCE` never become `IMPORTED_HISTORY`"* and *"a Sienna experience never becomes inherited evidence"*:

1. **DB CHECK** ties `timeline` to `source_type` on every `evidence` row (only `IMPORTED_HISTORY` ⇒ `INHERITED`).
2. **DB trigger** makes `evidence.source_type`/`timeline` immutable after insert — no UPDATE can flip a Sienna record into inherited.
3. **App-level provenance guard** (§3.5) is the *only* write path to `evidence`/`memory`; it stamps `timeline` from `source_type`, and refuses to create a `memory` whose linked evidence spans both timelines (`TimelineViolationError`).

### 1.5 DUE / STALE handling (no stored DUE)

`DUE` is computed by the scheduler query `WHERE status='OPEN' AND next_attention_at <= :now` (served by `ix_thread_due`). Only `OPEN → RESOLVED|DISMISSED|STALE` are ever written; `STALE` is set by an explicit scheduler pass over threads past `expected_resolution_at`.

### 1.6 Integrity audit query (used by M5 tests)

Proves no memory mixes timelines (the boundary claim, demonstrable to an examiner):
```sql
SELECT m.id FROM memory m
JOIN memory_evidence me ON me.memory_id = m.id
JOIN evidence e         ON e.id = me.evidence_id
GROUP BY m.id
HAVING COUNT(DISTINCT e.timeline) > 1
    OR MAX(e.timeline) <> m.timeline;   -- must return zero rows
```

### 1.7 Decisions expensive to change later (flagged)

1. **`source_type` enum + immutability + timeline-derivation** — the provenance anchor. Changing values/semantics later = migrating the anchor of the whole thesis. *Get right now.*
2. **TEXT-UUID PKs** — chosen over INTEGER for stable IDs (shown in Sienna's Mind + eval probe sets, survive delete/re-add, safe if multi-device sync is ever added). Reversing to INTEGER later touches every PK/FK. *Accepted deliberately.*
3. **Timestamps as ISO-8601 UTC TEXT** — switching to integer epoch later rewrites every row and time query.
4. **Soft-delete convention (`deleted_at` + retrieval filter)** — establishing tombstones now avoids a later "we can't explain why it vanished" migration; the privacy hard-delete path is layered on top.
5. **Polymorphic evidence ref (`ref_kind`/`ref_id`) + snapshot `text_snippet`** — makes evidence self-contained (survives source deletion). Moving to hard FKs later is a rewrite.
6. **`memory` keeps its rowid for FTS external-content** — never convert `memory` to `WITHOUT ROWID`; it would break `memory_fts`.
7. **`PRAGMA foreign_keys=ON` per connection** — if any code path forgets it, FKs silently don't enforce. Centralize connection creation so it can't be skipped.

### 1.8 Soft-delete retrieval invariant (Change 2)

**Invariant:** a memory with `deleted_at IS NOT NULL` must never participate in cognition, retrieval, context construction, embeddings/vector results, FTS results, or normal Sienna's Mind views.

Made hard to violate by two mutually-reinforcing mechanisms (belt **and** suspenders), chosen over relying on callers to append `deleted_at IS NULL`:

1. **Tombstoning physically removes the memory from every candidate source.** There is exactly one way to soft-delete — `MemoryRepository.soft_delete(memory_id)` — and in a single transaction it (a) sets `deleted_at`, (b) deletes the row's `memory_fts` entry, and (c) deletes its `embedding` rows. Because FTS and vector candidate generation read only `memory_fts` and `embedding`, a tombstoned memory **cannot be a candidate** — this directly satisfies "vector candidate generation cannot return deleted memories." The `memory` and `memory_evidence` rows are retained for provenance/audit and the privacy hard-delete path.
2. **All reads funnel through one canonical boundary.** Cognition, retrieval, context building, and Sienna's Mind never issue ad-hoc SQL against `memory`; they call a single `RetrievalRepository`/`MemoryReadRepository` whose base query applies `WHERE deleted_at IS NULL` centrally. A caller cannot accidentally see tombstones because the only query they can reach already excludes them.

Re-embedding/re-indexing paths skip tombstoned rows by construction (they iterate the canonical live query). **Test at M2:** create → tombstone → assert the memory is absent from FTS matches, vector candidates, the retrieval scorer's input, and default Sienna's Mind, while still present (tombstoned) for audit and hard-delete. *(Not built at M0 — memory does not exist until M2; this is the frozen spec M2 must satisfy.)*

---

## Deliverable 2 — Module / Package Layout

```
hellosienna/
├─ pyproject.toml                 # deps, entry point (single source of Python deps)
├─ alembic.ini
├─ README.md
├─ .gitignore                     # ignores build/venv; runtime data lives in LOCALAPPDATA, not here
├─ backend/
│  ├─ hellosienna/
│  │  ├─ __init__.py
│  │  ├─ main.py                  # (M0) entrypoint: start uvicorn thread + open pywebview window + wire shutdown
│  │  ├─ config.py                # (M0) resolves %LOCALAPPDATA%\HelloSienna paths, port, per-launch token, settings
│  │  ├─ logging_setup.py         # (M0) structured logging to console + LOCALAPPDATA\logs
│  │  ├─ shell/                   # DESKTOP SHELL — pywebview window; tray/notify/autostart land at M3
│  │  │  ├─ window.py             # (M0) create the native webview window pointed at the served SPA
│  │  │  ├─ tray.py               # (M3) pystray icon + minimize-to-tray
│  │  │  └─ notifications.py      # (M3) Windows toast (winotify)
│  │  ├─ api/                     # API BOUNDARY — the ONLY thing the UI talks to
│  │  │  ├─ app.py                # (M0) FastAPI app factory; binds 127.0.0.1; serves built SPA
│  │  │  ├─ auth.py               # (M0) per-launch token dependency (401 on mismatch)
│  │  │  ├─ schemas.py            # (M0) Pydantic request/response DTOs (API-facing, distinct from domain)
│  │  │  ├─ routes_health.py      # (M0) /api/health, /api/model/status (Ollama reachability)
│  │  │  ├─ routes_chat.py        # (M0) POST /api/chat (SSE token stream); GET /api/events (SSE push)
│  │  │  ├─ routes_memory.py      # (M4) read endpoints for Sienna's Mind
│  │  │  └─ routes_mind.py        # (M4/M7) inspect + (M7) correct/delete
│  │  ├─ core/                    # COGNITION / DOMAIN — pure Python; imports NO api/, NO shell/
│  │  │  ├─ clock.py              # (M0) Clock protocol, SystemClock, TestClock
│  │  │  ├─ domain.py             # (M0) enums + small value types (SourceType, Timeline, Importance, ThreadStatus)
│  │  │  ├─ conversation/         # (M1) turn orchestration: build context → stream reply → enqueue cognition
│  │  │  ├─ retrieval/            # (M2) hybrid candidate-gen + linear scorer + budgeter
│  │  │  ├─ memory/               # (M2) extraction + memory engine
│  │  │  ├─ attention/            # (M3) event/thread lifecycle + proactive-decision gates
│  │  │  └─ provenance.py         # (M2) THE storage-write guard (stamps + validates source_type/timeline)
│  │  ├─ providers/               # MODEL PROVIDERS — two independent abstractions
│  │  │  ├─ base.py               # (M0) LLMProvider + EmbeddingProvider Protocols + error types
│  │  │  ├─ ollama_llm.py         # (M0) OllamaLLMProvider.generate (+ complete_json at M2)
│  │  │  └─ ollama_embed.py       # (M2) OllamaEmbeddingProvider.embed
│  │  ├─ persistence/             # SQLITE — the single source of truth
│  │  │  ├─ db.py                 # (M0) engine/session; sets FK/WAL PRAGMAs in ONE place
│  │  │  ├─ models.py             # (M1+) SQLAlchemy models mapping §1.3
│  │  │  └─ repositories/         # (M1+) narrow data-access; evidence/memory writes are private to provenance.py
│  │  ├─ jobs/                    # BACKGROUND COGNITION — single-worker, never blocks foreground
│  │  │  ├─ queue.py              # (M2) single-worker queue + idempotency dedupe
│  │  │  └─ base.py               # (M2) Job contract
│  │  └─ scheduler/               # SCHEDULER — proactive ticks (uses Clock)
│  │     └─ scheduler.py          # (M3) APScheduler wiring + deterministic gates
│  ├─ migrations/                 # ALEMBIC (from M0)
│  │  ├─ env.py                   # sets foreign_keys=ON for migrations too
│  │  └─ versions/
│  └─ tests/
│     ├─ unit/                    # (M0) clock, auth, config, provenance guard
│     ├─ integration/             # (M0) migration apply, write/read round-trip, /api/health, streaming smoke
│     └─ evaluation/              # (M2+) probe-set harness (hits the API/core; no GUI)
└─ frontend/                      # REACT + TYPESCRIPT — zero Python; talks only to the localhost API
   ├─ package.json
   ├─ vite.config.ts
   ├─ tsconfig.json
   ├─ index.html
   └─ src/
      ├─ main.tsx                 # (M0) app bootstrap; reads per-launch token
      ├─ api/                     # (M0) the ONLY module that calls the API (client + token + SSE helpers)
      ├─ components/              # (M0+) shared UI
      └─ views/                   # (M0) Chat; (M4) SiennaMind
```

**Boundary summary (one line each):** `shell/` opens the window and, later, owns tray/notify; `api/` is the sole UI boundary and holds no cognition logic; `core/` is pure domain/cognition and imports nothing upward; `providers/` isolate model transport behind two Protocols; `persistence/` owns SQLite and centralizes PRAGMAs; `jobs/` runs cognition off the foreground path; `scheduler/` drives proactivity through the Clock; `frontend/` is Python-free and API-only; `tests/` + `tests/evaluation/` verify and measure. **Folders are created at the milestone shown in parentheses — not before** (no empty scaffolding).

---

## Deliverable 3 — Interface Contracts (definitions only)

Signatures and semantics; bodies are `...`. These freeze the shapes; implementation is authorized per milestone.

### 3.1 LLMProvider

```python
class LLMProvider(Protocol):
    """Owns transport to a text-generation model. Caller owns prompt construction and context budget."""

    async def generate(self, messages: list[ChatMessage], *, options: GenOptions | None = None
                       ) -> AsyncIterator[str]:
        """Stream response text chunks. Yields incrementally; raises before first yield on connect failure."""
        ...

    async def complete_json(self, messages: list[ChatMessage], schema: type[ModelT], *,
                            options: GenOptions | None = None) -> ModelT:   # (used from M2)
        """Return an instance of `schema` (a Pydantic model). May reparse/retry internally a bounded
        number of times; raises StructuredOutputError if it cannot produce schema-valid output."""
        ...
```
- **Errors:** `ProviderUnavailableError` (runtime unreachable), `ProviderTimeoutError`, `StructuredOutputError`. The provider does **not** implement business retries; callers/jobs decide policy.
- **Ownership:** nothing outside `providers/` knows the model name or transport. `generate` is the only path used at M0.

### 3.2 EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    """Independent of LLMProvider. Nothing may assume one object provides both."""
    model: str
    dim: int
    async def embed(self, texts: list[str]) -> list[list[float]]:   # (used from M2)
        """Return one vector per input text, each of length `dim`. Raises ProviderUnavailableError."""
        ...
```
- Ollama supplies both providers initially via two separate objects; the container wires them independently so either can be swapped alone.

### 3.3 Clock

```python
class Clock(Protocol):
    def now(self) -> datetime:   # MUST be timezone-aware UTC
        ...

class SystemClock:   # production
    def now(self) -> datetime: ...            # real UTC now

class TestClock:     # tests + demo time-advance
    def now(self) -> datetime: ...
    def set(self, when: datetime) -> None: ...
    def advance(self, delta: timedelta) -> None: ...
```
- **Ownership:** the single source of "now" in the entire system. Direct `datetime.now()`/`utcnow()` is banned in `core/`, `jobs/`, `scheduler/`; a unit test greps for violations. The demo's "advance to Thursday" is `TestClock.advance`.

### 3.4 Cognition / background-job contract

```python
class Job(Protocol):
    idempotency_key: str                 # deterministic from inputs; identical inputs => identical key
    async def run(self, ctx: JobContext) -> None: ...

class JobQueue(Protocol):                # single worker (M2)
    def enqueue(self, job: Job) -> None:
        """Non-blocking. Deduplicates by idempotency_key against pending/recent jobs."""
        ...
```
- **Foreground priority:** the worker runs off the request path; conversation endpoints never `await` a job. Jobs must not hold a DB write lock the foreground needs (WAL + short transactions).
- **Idempotency:** re-running a job yields the same DB state — extracted artifacts carry deterministic dedupe keys, so replays insert nothing new.
- **Failure:** a job failure is logged and never crashes the app; bounded retry with backoff; a poison job is dead-lettered (logged), not retried forever.

### 3.5 Provenance write / storage guard

```python
class ProvenanceGuard:
    """The ONLY write path to evidence and memory. Repositories for these tables are private to it."""

    def record_evidence(self, *, source_type: SourceType, ref_kind: RefKind, ref_id: str | None,
                        text_snippet: str, occurred_at: datetime | None) -> Evidence:
        """Stamps timeline = INHERITED iff source_type == IMPORTED_HISTORY else SIENNA (immutable).
        (From M6) requires imported_dataset_id present iff IMPORTED_HISTORY."""
        ...

    def create_memory(self, *, statement: str, evidence_ids: list[str], importance: Importance,
                      subject_person_id: str | None, event_time: datetime | None) -> Memory:
        """Sets memory.timeline from its evidence; raises TimelineViolationError if the evidence
        spans both timelines. Timeline is immutable thereafter."""
        ...
```
- **Errors:** `ProvenanceError`, `TimelineViolationError`. **Guarantee:** no other module can insert/alter `source_type`/`timeline`; DB trigger + CHECK back this up (§1.4).

### 3.6 API streaming contract (FastAPI ↔ React)

- **Bind:** `127.0.0.1:<ephemeral-port>` only. Never `0.0.0.0`.
- **Auth (Change 1 — one invariant, header only):** per-launch random token. FastAPI injects `window.__HS_TOKEN__` into the served `index.html` at launch (in-memory, not persisted by the frontend). **Every** protected request — plain requests *and* both SSE streams — carries `X-HS-Token: <token>` and nothing else; missing/wrong ⇒ `401`. **Native `EventSource` is not used** (it cannot set headers); the frontend consumes all SSE via authenticated streaming `fetch` + `ReadableStream`, which sets the header normally. The token must never appear in a URL/query string, a log line, persisted frontend state (no `localStorage`/`sessionStorage`), or any repository file. *(Loopback-only + per-launch token is defense-in-depth against other local processes, not network auth.)*
- **`POST /api/chat`** `{conversation_id, message}` ⇒ `text/event-stream` (read via `fetch` + `ReadableStream`):
  - `event: token` → `data: {"text": "<chunk>"}` (repeated, incremental)
  - `event: done`  → `data: {"message_id": "..."}`
  - `event: error` → `data: {"code": "...", "message": "..."}` (mid-stream failure; client keeps partial text + shows error)
- **`GET /api/events`** long-lived SSE for **server-initiated** pushes (proactive messages from M3, "state changed" pings), authenticated by the `X-HS-Token` header and consumed via authenticated streaming `fetch` (not native `EventSource`). Endpoint shape is frozen now so the React client is stable; it emits nothing until M3 (heartbeat comments only).
- **Errors:** transport/setup failures use HTTP status + `{"error":{"code","message"}}` envelope (never a raw stack trace to the client); in-stream failures use the `error` event above.

---

## Deliverable 4 — M0 Acceptance Contract

**M0 proves the skeleton is wired and disposable-shell-clean. It proves no intelligence.** Each criterion has a mechanical verification.

| # | Criterion | Verification procedure (done-when) |
|---|---|---|
| 1 | Repo structure works | Fresh clone → `pip install -e backend` (or `uv sync`) exits 0; `python -c "import hellosienna"` exits 0. |
| 2 | Python environment works | `python -m hellosienna --version` prints version and exits 0 in a clean venv; deps are pinned. |
| 3 | React dev environment works | `cd frontend && npm install && npm run build` exits 0; `frontend/dist/index.html` exists. `npm run dev` serves Vite. |
| 4 | pywebview opens the React UI | Launch app → a native window shows the built SPA reading "HelloSienna — M0". *(Manual check; automated smoke asserts the window object is created without exception.)* |
| 5 | FastAPI starts on loopback | `GET http://127.0.0.1:<port>/api/health` from localhost → `200`. Server is bound to `127.0.0.1` (assert config; a request to a non-loopback address is refused). |
| 6 | Per-launch API auth works | `curl` without header → `401`; with wrong token → `401`; with the launch token → `200`. Token value appears in **no** repo file and **no** log line. |
| 7 | React ↔ FastAPI communicate | UI panel shows "backend: ok" by calling `/api/health` with the injected token. |
| 8 | Ollama reachability/model status | `GET /api/model/status` reports `{ollama: reachable?, chat_model: present?, embed_model: present?}`. With Ollama stopped → returns a clean `unavailable` payload, **no crash**. |
| 9 | One streamed response reaches React | In the UI, send "hello" → tokens render **incrementally** (visibly progressive, not one blob); a `done` event closes the stream. *(M0 chat is a raw pass-through — not persisted, no memory.)* |
| 10 | SQLite initializes under `%LOCALAPPDATA%\HelloSienna\` | After first launch, `hellosienna.db` exists at that path (dir auto-created). File is **not** inside the repo tree. |
| 11 | Alembic migration applies | On launch (or `alembic upgrade head`), `0001_app_meta` applies; `alembic current` == head; `app_meta` table exists. |
| 12 | One write/read round-trip | App writes `app_meta('schema_initialized_at', clock.now())` and reads it back; written value == read value. |
| 13 | Clock abstraction works | Unit test: `SystemClock.now()` is tz-aware UTC within tolerance of real now; `TestClock.set/advance` moves `now()` deterministically. Lint/test finds zero `datetime.now()/utcnow()` in `core/`,`jobs/`,`scheduler/`. |
| 14 | Clean shutdown works | Quit the app → uvicorn thread stops, job worker (if started) cancels, DB connections close, process exits 0, port is immediately re-bindable, no orphaned python process. |
| 15 | Basic logging/error handling exists | Log file created under `%LOCALAPPDATA%\HelloSienna\logs\`; a forced endpoint error returns `{"error":{"code","message"}}` with a 4xx/5xx and no stack trace in the response body. |
| 16 | No private/runtime data in the repo | After a full run, `git status` is clean (DB/logs/token resolve to LOCALAPPDATA); a test asserts the resolved data dir is under `%LOCALAPPDATA%` and is not a subpath of the repo. |

### M0 non-goals (explicitly out of scope — do not start these during foundation)

- **No domain tables** beyond `app_meta` (no `evidence`, `memory`, `person`, `event`, `open_thread`, `conversation`, `message`, `sienna_self` — those begin at M1/M2/M3).
- **No cognition:** no extraction, no memory/belief/relationship/style, no retrieval, no embeddings, no FTS5. The job queue may exist only as an inert skeleton and runs no cognition.
- **No attention/proactivity:** no scheduler ticks, no events/threads, no notifications.
- **No tray / minimize-to-tray / start-on-login** (M3). The window merely opens and closes cleanly.
- **No import, no persona, no Sienna's Mind, no SQLCipher.**
- **No provider intelligence** beyond `generate` for the smoke test + a reachability probe (`complete_json`, `embed` are interface-defined but not exercised at M0).
- **Chat is not persisted and has no memory** — it exists only to prove end-to-end streaming.

---

### Approval gate

Approve these four deliverables (or mark changes) and I will request authorization to implement **M0 only**, against the acceptance table above — nothing from a later milestone.
