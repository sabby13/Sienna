# HelloSienna — Technical & Scope Assessment

**Role:** Senior software architect / AI engineer review
**Prepared for:** Sahib — university major project
**Constraints assumed:** ~3–4 months, solo · Windows · NVIDIA GPU 8–12GB VRAM · Python-strongest · grading weights product and research roughly equally
**Status:** Pre-implementation. No code yet. This document is for us to agree on **scope → stack → architecture → schema → milestones** before building.

> One-line verdict: The core idea is coherent and genuinely distinctive, your engineering instincts are already good, and the main threat to this project is **not** technical difficulty — it's **scope**. Your "Required Core" is a 6-month spec wearing a 3-month deadline. Cut it to a spine and you have an excellent, defensible major project.

---

## A. Product Assessment

**Is the central idea coherent?** Yes. "A persistent companion that remembers, maintains continuity, notices what matters, and follows up" is a real, unifying product thesis, and — importantly — it's one that most commercial chatbots *deliberately don't* do. The distinction you draw between **memory ("what happened")** and **attention ("what still matters")** is the sharpest idea in the whole brief. That single distinction is your thesis, your demo climax, and your best exam answer. Protect it.

**What is genuinely distinctive** (keep these, they are the project):

1. **Provenance-aware memory** with a real source taxonomy instead of a real/fake flag. This is academically defensible and rare in student work.
2. **The two-timeline separation** (inherited history vs. Sienna-era experience) with the rule that a generated experience never becomes evidence about the imported person. This is the most intellectually honest design decision in the document and it's a great viva talking point.
3. **Temporal attention / open threads** driving proactive follow-up. This is what makes the system *feel* alive and is the hardest thing to fake.
4. **"Sienna's Mind" inspectability.** This does double duty: it's a product feature *and* your explainability evaluation. Build it early, not last.

**What is a gimmick or a trap** (be honest with yourself here):

- **The "initialize from a real person's WhatsApp export" framing is the biggest risk in the product, and it is more of an ethical/privacy landmine than a technical one.** Cloning the style of a real, possibly still-living person you have a relationship with — from private messages — is the kind of thing that gets flagged in an ethics review and makes an examiner uncomfortable if you present it naively. **Recommendation:** keep the import pipeline (it's technically the richest component), but reframe it in your report as *"style/persona initialization from a consenting-source conversation corpus,"* require explicit consent as a first-class step, and demo it on **your own** exported chats or a synthetic/opt-in corpus. Do not demo it on a third party's messages without their consent. This reframing costs you nothing technically and removes a real hazard.
- **"Belief system" risks turning into a fake AI-research showpiece.** A confidence score like `0.78` implies a probabilistic model you will not actually have. Keep beliefs, but make the confidence *honestly* a coarse, rule-derived label (e.g. `low/medium/high` from evidence count and recency), and say so plainly in the report. A simple, honest mechanism you can defend beats a sophisticated one you can't.
- **"Relationship model" can balloon.** The 11-attribute list in §10 is a wish list. For v1, three or four learned dimensions (directness, warmth/humor, proactivity tolerance) plus a free-form notes/preferences store is enough to demonstrate the idea.

**What to simplify or remove for v1:** style-model sophistication (§17's 13 characteristics → ~5), belief confidence math (→ coarse labels), relationship dimensions (→ 3–4), and the tool system (→ exactly one local-files tool, as you already proposed — that instinct is correct).

---

## B. Major-Project Scope Assessment

**Blunt answer: yes, even the "Required Core" is too large for 3–4 months solo.** Not because any single item is hard, but because 21 interlocking subsystems each need design + build + test + a paragraph in the report, and the integration tax between them is where solo projects die. You said it yourself: *"I would rather finish a coherent system than have 30 half-working features."* Hold that line.

I recommend **three concentric targets**. The inner ring must be *done and demoable*; the middle ring is your actual submission goal; the outer ring is bonus.

### Tier 1 — Minimum Demonstrable System (MDS) · "the spine" · target ~week 8
The smallest thing that tells the whole story *Remember → Understand → Continuity → Care → Act*.

| # | Capability | Why it's in the spine |
|---|---|---|
| 1 | Windows desktop app (Python core + web UI) | The vessel |
| 2 | Local LLM via Ollama, streaming conversation | The voice |
| 3 | Persistent conversation history (SQLite) | Baseline persistence |
| 4 | Persistent Sienna identity outside the model | Core claim: identity ≠ weights |
| 5 | Provenance-aware **Memory** (with `source_type`) | The thesis |
| 6 | **Events** extracted from messages | Enables temporal reasoning |
| 7 | **Open Threads** with a `next_attention_at` | The attention thesis |
| 8 | Hybrid retrieval (FTS + vector + recency + thread), **explainable** | The academic core |
| 9 | Proactive follow-up via in-app scheduler + deterministic gates | Makes it feel alive |
| 10 | "Sienna's Mind" inspection UI (read-only first) | Product + explainability |
| 11 | Two-timeline separation enforced in the schema | The honesty argument |

**If everything after week 8 caught fire, this is still a submittable project** with a real demo and real evaluation.

### Tier 2 — Major-Project Target (MPT) · your real finish line · target ~week 13
MDS **plus**:

- **Import pipeline** for WhatsApp/plain-text export → normalized messages → chunked extraction → consolidated **style profile** + seeded memories/events, with evidence links back to source messages.
- **Structured style model** (≈5 features) + representative-example retrieval used in prompting.
- **Minimal relationship state** (3–4 dimensions + preferences/notes, user-correctable).
- **Basic evolving beliefs** with supporting/contradicting evidence IDs and coarse confidence; supersession instead of overwrite.
- **Memory correction/deletion + belief-is-wrong** in Sienna's Mind (write path).
- **Tool + permission abstraction** and **one local-files tool** (discover → propose → permission → execute → summarize).
- **Academic evaluation** run and written up (Section J).

**This is the project you defend.** Everything in your original "Required Core" is here except the parts I folded together (see below).

### Tier 3 — Stretch (only if MPT lands early)
Richer belief evolution; additional import formats; better proactivity learning; a second tool; memory-decay experiments.

### Explicitly Future (agree to *not* touch — say so in the report as scoped-out)
Gmail/calendar/LinkedIn/X/shopping automation, autonomous browser, voice, 3D avatar, multi-agent, large knowledge graph, fine-tuning/LoRA. Your instinct to future-work these is correct; naming them as *deliberately* out of scope is itself good engineering judgment to show an examiner.

### Scope simplifications baked into the tiers (these are the cuts)
- **Merge `AttentionItem` into `OpenThread`.** You do not need three temporal tables. `Event` = a dated fact extracted from text. `OpenThread` = an unresolved matter that carries its own `next_attention_at`, `importance`, and status. The scheduler simply queries threads that are due. This removes an entire subsystem and its sync bugs. (Details in F/I.)
- **`DUE` is a computed state, not a stored one.** A thread is "due" when `now ≥ next_attention_at AND status = OPEN`. Storing it invites drift. Store `OPEN / RESOLVED / DISMISSED`, derive `DUE`, and transition to `STALE` only via an explicit scheduler pass.
- **Beliefs are Tier 2, not Tier 1.** The spine works without them; they're the enrichment that makes Sienna's Mind impressive.

---

## C. Architectural Critique

**Weak assumptions**
- *"Local-first with local models will feel responsive enough."* On 8–12GB VRAM a quantized 7–8B model streams at a usable but not instant rate, and **background cognition (extraction) competes with the same GPU**. If you fire extraction the moment a reply finishes, the *next* user turn stalls. **Mitigation:** a single-worker background queue that runs cognition when the model is idle, and never blocks the foreground reply. Assume one model loaded at a time; don't assume you can run chat + extraction concurrently at full speed.
- *"Import → rich persona automatically."* Extraction quality from a small local model is mediocre and noisy. Assume you will hand-tune prompts and that some extractions will be wrong — which is exactly why provenance + user correction matter, and why you should *say that in the report* rather than pretend extraction is clean.
- *"Confidence 0.78" implies calibration you won't have.* Already covered — make it honest.

**Unnecessary complexity to drop now:** microservices (you already said no — good), a second database, a vector DB, a probabilistic inference engine, multiple models for different tasks in v1 (one chat model + one embedding model is plenty), and a message bus for background cognition (an in-process queue is enough).

**Missing components you'll wish you had:**
- **A migrations story from day one.** You *will* change the schema. Use a real migration tool (Alembic if you use SQLAlchemy, or a tiny hand-rolled `PRAGMA user_version` stepper). Not optional.
- **An idempotency/versioning story for background cognition.** Re-running extraction on the same conversation must not duplicate memories. Give extractions a deterministic dedupe key.
- **A "time provider" abstraction.** Your demo needs to *advance the clock* (§28 step 8). If you read `datetime.now()` everywhere you can't simulate Thursday. Route all "now" through one injectable clock. This is a small decision that saves the demo.
- **Structured LLM output validation.** LLMs return malformed JSON constantly. Use a schema validator (Pydantic) on every structured extraction and treat failures as "no extraction," not crashes.

**Privacy/security risks** (you flagged this in §24 — here's the concrete list for a student build):
- Imported relationship chats are the most sensitive data in the system. Store the SQLite DB and any raw exports **in the user's local app-data directory, not in the repo, not in OneDrive-synced folders** (note: your working folder is under OneDrive — that would silently sync private chats to the cloud; explicitly keep the data store out of synced paths).
- **Encryption at rest is a reasonable, defensible feature:** SQLCipher (encrypted SQLite) with a key derived from a user passphrase via a KDF. This is a strong, examinable privacy story and not much work. If SQLCipher's Python packaging fights you under deadline, fall back to encrypting just the raw-export files and documenting the tradeoff.
- **Never send data off-device without an explicit, visible action.** Since the default backend is local Ollama, this is naturally satisfied — make it a stated invariant and a test.
- **Right to be forgotten:** deletion in Sienna's Mind must actually delete evidence + dependent memories (or tombstone them), and you should be able to demonstrate it. Good ethics-section material.
- **Secrets:** even for a local-files tool, sandbox the tool to a user-selected root directory; never let a tool call resolve paths outside it. Path-traversal is the one security bug a file tool will actually have.

**Memory problems to anticipate:** extraction duplication, memory sprawl (thousands of low-value memories drowning retrieval — hence importance weighting), and the belief/evidence graph growing faster than you can inspect it. **Retrieval problems:** vector-only recall misses exact names/dates (hence FTS + entity match), and recency can swamp relevance (hence weighting, not filtering). **Persona problems:** local small models drift out of style over long chats; "act like this person" prompting produces caricature — your structured-style + examples approach is the right correction, and comparing the two *is* your persona experiment. **Attention/proactivity problems:** the failure mode is *annoying the user*; your deterministic gates are the right answer, and a low daily budget (2–3) is safer than clever LLM judgment.

**Windows-specific issues:** true background execution when the app is closed is awkward (see D — I recommend a tray-resident app, not a Windows Service). File paths, app-data directories (`%LOCALAPPDATA%`), and PyInstaller packaging with an Ollama dependency are the real friction points, not the AI.

**Local-model limitations:** weaker instruction-following and JSON reliability than frontier models; smaller context windows (plan for ~8k usable tokens, not 128k); slower structured extraction. Design the context budget (Section §19) around a *small* window and you'll be safe everywhere.

---

## D. Technology Decision

Given Python-strongest + solo + 3–4 months + "build the brain before the hands," the stack should keep you in Python for everything that carries academic weight, and spend as few "novelty tokens" as possible on the shell.

### Recommended primary stack

| Layer | Choice | Why (and what I rejected) |
|---|---|---|
| **Core / cognition** | **Python 3.11+** | Your strength; best local-AI ecosystem; the cognitive architecture is the project and must be in the language you debug fastest. Rejected C#/Rust: you'd spend the project learning the language instead of the ideas. |
| **App architecture** | **Local FastAPI backend + web UI, wrapped in a desktop window** | One process model you fully understand. The UI talks to `localhost`. |
| **Desktop shell** | **pywebview** (primary) — a native OS webview hosting your UI, driven from Python; package with **PyInstaller** | Keeps you 100% in Python, no Node build toolchain, no Rust. **Rejected Tauri:** great installer but Rust shell + sidecar management is a distraction you can't afford. **Rejected Electron:** heavy, drags in a full JS build/runtime for little gain here. **Rejected .NET/WinUI:** cleanest *Windows* story but exiles you from the Python AI ecosystem. If pywebview's packaging frustrates you, the fallback is **Tauri with a PyInstaller'd Python sidecar** — but only if you have time to spare. |
| **UI** | **React + Vite + TypeScript**, or plain HTML/HTMX if you want zero JS build | "Sienna's Mind" (evidence graphs, belief cards, thread lists) benefits from React's componentization. If JS isn't your comfort zone, HTMX + server-rendered templates is a legitimate, lower-risk choice — pick based on which you'll actually finish. |
| **Source of truth** | **SQLite** (single file), accessed via **SQLAlchemy** + **Alembic** migrations | One database. Do not add a second. |
| **Full-text search** | **SQLite FTS5** (built in) | No new dependency; excellent keyword/entity recall. |
| **Vector search** | **Embeddings stored as BLOBs; brute-force cosine in NumPy** for v1 | At a few thousand memories this is *milliseconds* and trivially explainable in the report. **Upgrade path:** `sqlite-vec` extension if the corpus grows — same DB, no architecture change. **Rejected:** a dedicated vector DB (Chroma/Qdrant/etc.) — an unjustified second datastore. |
| **Encryption** | **SQLCipher** (encrypted SQLite) via passphrase-derived key, with a graceful fallback | Strong, examinable privacy story. |
| **LLM abstraction** | `LLMProvider` interface → `OllamaProvider` (default) | Exactly as you proposed. Keep the interface tiny: `generate(stream)`, `complete_json(schema)`, `embed()`. |
| **Chat model** | A **quantized 7–8B instruct model** via Ollama (pick the current best small model at build time — the Qwen2.5-7B / Llama-3.1-8B class fits 8–12GB at Q4) | Comfortable on your GPU with room for the embedding model. Don't hard-code one; make it a config setting so you can swap as better small models ship. |
| **Embedding model** | A small local embedder via Ollama (e.g. the `nomic-embed-text` class) | Tiny VRAM footprint; runs alongside the chat model. |
| **Background processing** | **In-process `APScheduler`** ticking every N minutes inside a **system-tray-resident app**; all "now" via an injectable **clock** | Proactive checks run while the app lives in the tray. **Rejected:** a Windows Service or waking a closed app — disproportionate effort; document "proactivity runs while Sienna is running (tray)" as a scoped decision. The injectable clock lets you fast-forward time in the demo. |
| **Structured output** | **Pydantic** models validated on every extraction | Turns flaky LLM JSON into safe, typed updates or clean no-ops. |
| **Packaging** | **PyInstaller** one-folder build + a note that **Ollama is a prerequisite** the user installs separately; data in `%LOCALAPPDATA%\HelloSienna\` (explicitly **not** OneDrive) | Bundling model weights is impractical; a first-run check that Ollama is reachable and pulls the model is the pragmatic answer. |

**Net: one Python process, one SQLite file, one local model runtime, one webview window.** That is a system one student can understand, debug, explain, and defend — which is your stated objective.

---

## E. Cognitive Architecture (refined)

Keep your logical modules, but tighten responsibilities and — critically — mark every operation as **deterministic (code)** or **LLM**. This table *is* your architecture diagram for the report.

| Module | Responsibility | Deterministic (code) | Uses LLM |
|---|---|---|---|
| **Conversation Engine** | Orchestrates a turn: build context → stream reply → enqueue cognition | Turn flow, streaming plumbing, persistence | Reply generation |
| **Context Engine** | Assembles the bounded prompt from retrieved parts within a token budget | Budgeting, ordering, truncation | — |
| **Retrieval** | Finds candidate memories/threads/examples and ranks them | Candidate gen (FTS/vector/entity/recency/thread), scoring, reranking | — (embeddings are a model call but the algorithm is code) |
| **Memory Engine** | Stores evidence; extracts memories; dedupes | Storage, dedupe keys, provenance stamping | Extraction, summarization |
| **Belief System** | Holds beliefs + evidence links; supersedes | Confidence labeling, supersession, evidence graph | Proposing/updating beliefs (validated by code) |
| **Relationship Model** | Tracks interaction-style preferences | Storage, updates from explicit user correction | Optional inference of style prefs |
| **Sienna Self Model** | Stable + evolving identity, outside the weights | Storage, stable-fact protection | Optional self-reflection updates |
| **Attention Engine** | Open threads + their due times; scheduler | Thread lifecycle, `next_attention_at`, all gates | Bounded "is this worth raising now, and how" judgment |
| **Tool Engine** | Discover/propose/execute one tool | Execution, sandboxing, result capture | Deciding *whether* a tool is relevant; summarizing results |
| **Permission Manager** | Gates consequential actions | Everything | — |
| **LLM Provider** | Abstraction over Ollama | Interface | — |
| **Persistent Storage** | SQLite source of truth | Everything | — |

**Data flow, foreground (must be fast):**
`user message → Retrieval → Context Engine (bounded prompt) → LLM stream → UI → persist message`.

**Data flow, background (must not block foreground):**
`enqueue(conversation window) → Memory extraction → Event extraction → Thread create/resolve → Belief update proposals → validate (Pydantic + rules) → persist`.

**The invariant that protects your thesis:** every write carries a `source_type`, and **`SIENNA_EXPERIENCE`/`SIENNA_INFERENCE` records can never be written into `IMPORTED_HISTORY` evidence.** Enforce it at the storage layer, not by convention — a single guard function that stamps and validates provenance on every insert. This is the one line of defense for your "evolution, not rewriting history" claim, and an examiner will poke at exactly this.

**The progression Evidence → Memory → Belief → Attention** is a *pipeline of optional promotions*, not an automatic cascade: extraction decides which evidence becomes memory; belief updates fire only on enough corroboration; a thread is created only when an event/statement implies a future unresolved matter. Say this explicitly — "not every X becomes Y" is a design strength, not a gap.

---

## F. Data Model (initial, deliberately lean)

Entities to build now (I've cut your §7 list where tables would be speculative):

- **Conversation** — a chat session. `id, started_at, kind (SIENNA | IMPORT), meta`.
- **Message** — `id, conversation_id, sender (USER | SIENNA | IMPORTED_PARTICIPANT), text, ts, source_type`.
- **Evidence** — the raw anchor. `id, source_type (enum), ref (→ message/document/import), text_snippet, ts, imported_dataset_id?`. Everything traces back here.
- **Memory** — `id, statement, importance (0–1 or low/med/high), ts_event?, subject_person_id?, created_at, source_type`. Linked to Evidence via **MemoryEvidence** (many-to-many).
- **Event** — `id, title, event_time, status (UPCOMING | PAST | UNKNOWN_OUTCOME), importance, source_evidence_id`.
- **OpenThread** — `id, topic, status (OPEN | RESOLVED | DISMISSED | STALE), importance, next_attention_at, expected_resolution_at?, created_at, resolved_at?, linked_event_id?`. **(AttentionItem folded in here.)**
- **Belief** — `id, statement, confidence_label, status (ACTIVE | SUPERSEDED), superseded_by?, created_at`. Linked via **BeliefEvidence** with a `role (SUPPORTS | CONTRADICTS)`.
- **Person** — `id, kind (USER | IMPORTED_PERSON | OTHER), display_name`. (You need this to attach memories/beliefs to *who* they're about — central to the two-timeline separation.)
- **SiennaSelf** — small key/value or a single row of structured fields: `stable_identity (protected), evolving_traits, style_profile_id`.
- **RelationshipState** — `id, directness, warmth, proactivity_tolerance, preferences_json, updated_at`. (3–4 dimensions + free-form.)
- **StyleProfile** — structured style features (≈5) + a pointer to representative example message IDs.
- **ImportedDataset** — `id, source_kind, imported_at, participant_names, message_count`. Provenance root for everything from an import.
- **ToolAction** — `id, tool, args, permission_status, result_summary, ts`. (Needed to *show* permission→execution in the demo.)
- **Embedding** — `owner_type, owner_id, vector (BLOB), model, dim`. One table serving memories/examples.

**Deferred / merged (do NOT build yet):** `AttentionItem` (merged into OpenThread), `Project` (model it as a `Person`-like entity *only if* the demo needs it — otherwise a Memory with `subject` is enough), `SourceReference` as a separate table (it's the `Evidence.ref` column).

**Schema decisions that are painful to reverse later — get these right on day one:**
1. **Provenance on every record** (`source_type` + evidence links). Retrofitting provenance after the fact is a rewrite.
2. **The two-timeline boundary** — modeled via `Person.kind` + `source_type`, enforced in a storage guard. This is your thesis; changing it late touches everything.
3. **Evidence as the universal anchor.** If memories/beliefs don't point back to evidence from the start, explainability becomes archaeology.
4. **The injectable clock / `ts` everywhere in UTC.** Store UTC, render in the user's TZ (you're UTC+5:30). Fixing timezone assumptions late is miserable.
5. **Migrations from commit #1.** Adding Alembic after you have real data is annoying; before, it's free.

Everything else (adding vector search, more style features, more beliefs, a second tool) is cheap to add later. Spend your "get it right early" budget only on the five above.

---

## G. Retrieval Architecture (v1, hybrid, explainable)

Designed to be *defensible*: every candidate has a reason, every score is a transparent weighted sum you can print in Sienna's Mind.

**Step 1 — Candidate generation (union of cheap recalls):**
- **FTS5 keyword/entity match** on memory statements (catches exact names, places, dates).
- **Vector top-K** (cosine over BLOB embeddings, NumPy) on the current message + short conversation summary.
- **Entity/name exact match** — pull memories whose `subject_person` or named entities appear in the message.
- **Active-thread pull** — always consider OPEN threads (attention shouldn't need semantic luck to surface).
- **Recency window** — last N memories, so "we just talked about this" always survives.

**Step 2 — Scoring (linear, weighted, printable):**
```
score(m) = w_sem * semantic_similarity(m)
         + w_rec * recency_decay(m)         # exp decay on age
         + w_imp * importance(m)
         + w_tmp * temporal_relevance(m)    # boost if m relates to a due/near event
         + w_thr * thread_relevance(m)      # boost if m attached to an active thread
         + w_ent * entity_match(m)          # boost on exact name/entity hit
```
Start weights equal-ish, tune on your probe set (Section J). Because it's linear you can show *why* each memory was retrieved — which is both your explainability feature and a clean ablation study ("drop the temporal term, watch Recall@K fall").

**Step 3 — Rerank & dedupe:** sort by score, drop near-duplicates (same dedupe key / high mutual similarity), keep top-N.

**Step 4 — Context budgeting (Section §19):** fill categories in priority order until the token budget is spent — Sienna identity (fixed, small) → active threads → top memories → representative style examples → relevant beliefs → recent turns → current message. Each category gets a cap so no single category can crowd out the others. Assume a **small usable window (~8k tokens)** and this behaves well on any model.

**Why not vector-only:** it misses exact names/dates, ignores time, and can't represent "this is an open worry." The hybrid is only ~5 code terms more than a top-K call and buys you the entire academic story. Keep it.

---

## H. Import Pipeline

`Export file → Parser → Normalized Messages → Chunker → per-chunk Extraction (map) → Hierarchical Consolidation (reduce) → StyleProfile + seed Memories/Events + Embeddings`, with evidence links preserved throughout.

1. **Parse.** WhatsApp `_chat.txt` has a stable-ish line format (`[dd/mm/yy, hh:mm:ss] Name: message`, plus multi-line continuations, `<Media omitted>`, and system lines). Write a tolerant regex parser with a fallback for "line that isn't a new message → append to previous." Plain-text and simple JSON get their own tiny adapters behind one `Parser` interface. **Anonymize/consent step here:** record participant names, flag which is the user, and gate the whole thing behind an explicit "I have consent to import this" confirmation.
2. **Normalize** into `Message` rows under one `ImportedDataset` (all `source_type = IMPORTED_HISTORY`).
3. **Chunk** by time-window or fixed message count (e.g. ~40 messages) with small overlap, so context isn't cut mid-thought.
4. **Extract per chunk (map)** with *separate, small, schema-constrained* prompts — don't ask one mega-prompt for everything:
   - style signals (length, emoji, slang, punctuation, common phrases),
   - events (dated things), facts about the user, relationship memories, representative example messages.
   Validate each with Pydantic; a failed parse = skip, log, continue.
5. **Consolidate hierarchically (reduce):** merge per-chunk style signals into one `StyleProfile`; dedupe events/memories; pick a handful of representative examples. Do it in two levels (chunk → batch summary → global) so you never feed the whole history to the model at once — exactly as your §16 demands.
6. **Embed** the seeded memories and examples.
7. **Evidence retention:** every seeded memory/event points to the source `Message`(s). This is what lets Sienna's Mind show "I know this because you said it on 3 March."
8. **Failure/retry:** the whole import is resumable and idempotent — each chunk has a deterministic id, re-running skips already-extracted chunks, and a crash mid-import leaves a consistent partial dataset, not garbage. Cap total LLM calls and show a progress bar (imports of a big history can take minutes on local models — set that expectation in the UI).

**Reality check for the report:** local-model extraction will be imperfect. That's fine — it's *why* provenance + user correction exist. Frame extraction as "best-effort, user-correctable, evidence-linked," not "accurate."

---

## I. Attention Architecture

**Event vs. Thread (kept distinct, `AttentionItem` removed):**
- **Event** = an extracted dated fact ("interview, Thursday 11:00"). Passive.
- **OpenThread** = an unresolved *matter* that wants future action ("interview outcome — follow up"). Carries its own `next_attention_at`. A thread may reference an event, but not every event spawns a thread and not every thread has an event.

**OpenThread lifecycle:** `OPEN → (RESOLVED | DISMISSED | STALE)`.
- **OPEN** on creation. `next_attention_at` set from the event time (a pre-event check-in and/or a post-event follow-up).
- **DUE** is *derived*: `now ≥ next_attention_at AND status = OPEN`. Not stored.
- **RESOLVED** when the user reports an outcome (detected in background cognition) or explicitly in Sienna's Mind.
- **DISMISSED** when the user says "drop it" (explicit).
- **STALE** set by a scheduler pass when a thread is long past `expected_resolution_at` with no resolution — moves it out of active attention without deleting it.

Your five-state model is *almost* right; my only change is **don't store DUE** (derive it) — storing a computed state is the classic source of "why is this thread stuck in DUE forever" bugs.

**Scheduler + proactive decision (deterministic first, LLM last):**
```
APScheduler tick (every N min, in the tray app)
  → query OpenThreads where DUE (now ≥ next_attention_at)
  → deterministic GATES (hard filters):
        quiet hours? · within notification cooldown? · daily proactive budget spent?
        · importance ≥ min? · user recently active/mid-conversation? · previously dismissed?
        · proactivity level (user setting)?
  → survivors only: ONE bounded LLM judgment
        "Given this thread + context, is it worth raising now? If yes, one short message."
        (schema: {should_raise: bool, message: str|null, reason: str})
  → if should_raise and still within budget: create proactive message / OS notification
  → update thread (reschedule next_attention_at or mark handled)
```
**Notification policy:** low daily budget (2–3), a cooldown between proactive messages, quiet-hours honored, and every proactive message logged with its reason (for the demo *and* the "did we over-notify?" experiment). **The LLM never gets to decide *whether it's allowed* to notify — only what to say once code has already permitted it.** This is the single most important safety property of the proactivity system; state it as an invariant.

**Thread resolution detection** is a background-cognition task: when a new user message arrives, check whether it plausibly resolves any OPEN thread (semantic + entity match → bounded LLM confirm) and, if so, propose `RESOLVED` (validated before commit). This closes the loop in your demo: user mentions the interview went well → thread auto-resolves → Sienna's Mind updates live.

---

## J. Academic Evaluation Plan

Balanced grading means you need *real numbers*, but as a solo undergrad you must pick experiments that are **cheap to run and honest about n**. Here's what's realistic; I've cut the parts that need a user study you don't have time for.

**Build one asset first: a probe set.** ~40–60 hand-written questions over a fixed seeded corpus, each labeled with the `memory_id`(s) that *should* be retrieved. This single artifact powers experiments 1 and 2 and is the highest-leverage thing you can build for the report.

1. **Retrieval quality (strong, do this).** On the probe set: **Recall@K, Precision@K, MRR**, plus **retrieval latency** and **context tokens used**. **Ablations** (drop each scoring term) are easy with your linear scorer and make a genuinely good results section. This is your headline experiment.
2. **Context efficiency (strong, do this).** Compare *full available context* vs *HelloSienna-selected context* on the probe questions: **% token reduction** and **whether the needed info was still present** (answerable-rate). This directly demonstrates the product thesis with numbers.
3. **Persona/style reconstruction (medium, do a small honest version).** Three conditions — (A) base model, (B) persona *prompt only*, (C) structured style + retrieved examples + relationship context. **Automatic style metrics** vs the source corpus (avg message length, emoji rate, type-token ratio, punctuation/casing rate) are free and objective. Add a **small blind human rating** (3–5 raters, similarity 1–5) — small n, reported honestly, is acceptable at undergrad level. Also report a rough **hallucination/consistency check**.
4. **Provenance correctness (medium, cheap).** Hand-label a sample of extractions; report **precision of `source_type` assignment** and correctness of evidence links. Directly evidences your central claim.
5. **Temporal attention (strong, scripted — no humans needed).** A deterministic timeline test: inject events/statements, **advance the injectable clock**, and assert the system creates the right thread, fires follow-up at the right time, resolves on outcome, and — crucially — measure the **false-notification rate** (did it nag when it shouldn't?). This is a clean, reproducible experiment that most student projects can't offer.
6. **Explainability (qualitative, but show it).** Demonstrate, via Sienna's Mind, that for any memory/belief/thread you can answer *why remembered / where it came from / why it's on Sienna's mind.* Frame as a walkthrough, not a metric.

**Cut / don't attempt:** large-scale user studies, statistically-powered persona A/Bs, and anything needing many participants. Say in the report that these are future work — examiners respect a scoped evaluation over an overclaimed one.

---

## K. Development Roadmap

Milestones, each producing something testable, ordered so you never build a later system before its foundation. Assuming ~14 weeks and part-time-solo intensity. **The viable-submission line is at the end of M5.**

- **M0 — Skeleton (wk 1).** pywebview window + FastAPI + SQLite + Alembic + Ollama round-trip; injectable clock; config; data dir in `%LOCALAPPDATA%`. **Accept:** app opens, streams one hard-coded local-model reply, writes/reads a row, a migration runs.
- **M1 — Conversation + persistence (wk 2).** Real streaming chat, Message/Conversation storage, conversation history UI. **Accept:** close and reopen; full history persists; identity system-prompt loaded from `SiennaSelf`.
- **M2 — Memory + provenance + retrieval spine (wk 3–4).** Evidence/Memory/Person tables with the provenance guard; background extraction (validated); embeddings; the hybrid retriever (FTS + vector + recency + entity) with printable scores. **Accept:** ask about something said earlier, correct memory is retrieved, and you can *see the score breakdown*. Probe-set v1 started.
- **M3 — Events + Open Threads + attention (wk 5–6).** Event/OpenThread tables; thread creation from events; APScheduler; deterministic gates; bounded proactive judgment; tray app + notification. **Accept:** tell Sienna about a future event → thread appears; advance clock → Sienna proactively follows up; gates provably suppress spam. **This is the thesis working end-to-end.**
- **M4 — Sienna's Mind, read-only (wk 7).** The four+ panels (On My Mind / What I Know / What I Believe (stub) / Our Memories / Inherited History) reading real state, with evidence drill-down. **Accept:** every item shows its provenance/why.
- **M5 — Two-timeline hardening + MDS demo (wk 8).** Enforce/verify the inherited-vs-Sienna boundary; end-to-end MDS demo dry-run. **Accept:** the full *Remember→Continuity→Care* story runs on seeded data. **← Minimum submittable project reached here.**
- **M6 — Import pipeline (wk 9–10).** Parser → chunk → extract → consolidate → StyleProfile + seeds + evidence links; consent/anonymize step; progress UI; idempotent/resumable. **Accept:** import a real (own/consented) export → style profile + seeded memories appear with source links.
- **M7 — Style in prompting + relationship + beliefs + write-path Mind (wk 11–12).** Structured style + example retrieval in the prompt; 3–4-dim relationship state; basic beliefs with evidence + supersession; memory/belief correction & deletion in Sienna's Mind. **Accept:** persona conditions A/B/C runnable; a belief can be marked wrong and supersedes without erasing evidence.
- **M8 — One tool + permissions, and evaluation (wk 13).** Tool/permission abstraction + local-files tool (discover→propose→permission→execute→summarize, sandboxed to a chosen root); run experiments 1–5; write results. **Accept:** the §28 demo runs start-to-finish; results tables exist.
- **wk 14 — Buffer / report / demo polish.** No new features. (Solo projects always need this; protect it.)

If you slip, you *stop adding* and fall back to the last green milestone — because every milestone is independently demoable, a slip degrades gracefully instead of leaving you with nothing.

---

## L. Top 10 Risks & Mitigations

1. **Scope overrun (the #1 killer).** → Freeze scope at the MPT tier; treat the MDS (end of M5) as the real deadline and everything after as upside. Review scope at M3 and M5 and cut, don't add.
2. **Local-model quality/latency (extraction is noisy, GPU is shared).** → One model loaded at a time; background cognition runs only when foreground is idle; keep the context window small (~8k); accept and *design around* imperfect extraction via provenance + correction.
3. **Background cognition corrupting state (dupes, bad JSON, race with foreground).** → Pydantic-validated updates, deterministic dedupe keys, single-worker queue, and the provenance guard rejecting illegal writes. Never let a malformed extraction crash a turn.
4. **The two-timeline boundary leaking** (a Sienna experience becoming "evidence" about the imported person). → Enforce in one storage guard, not by convention; add a test that tries to violate it and asserts rejection. This is the claim examiners will probe.
5. **Attention system becoming annoying / firing wrongly.** → Deterministic gates *before* any LLM judgment; low daily budget; quiet hours; log every decision; the scripted timeline test (J-5) catches regressions.
6. **Privacy incident with imported chats** (esp. OneDrive sync of your working folder). → Data store in `%LOCALAPPDATA%`, never a synced path; SQLCipher at rest; explicit consent step; real deletion. Write the ethics/consent section early.
7. **Packaging hell** (PyInstaller + webview + Ollama dependency near the deadline). → Do a throwaway packaged build at **M1**, not week 14; document "Ollama is a prerequisite" and add a first-run reachability check rather than bundling weights.
8. **Retrieval that looks fine in demo but has no numbers.** → Build the probe set at M2; wire metrics in as you go, not at the end. Balanced grading punishes "trust me, it remembers."
9. **Demo can't show the passage of time.** → The injectable clock from M0 makes "advance to Thursday" a UI button. Rehearse the §28 flow at M5 and again before submission.
10. **Solo burnout / single point of failure.** → Weekly green-milestone checkpoints, the wk-14 buffer, and the graceful-degradation property (last green milestone is always demoable) mean a bad week costs a feature, not the degree. Commit often; the schema-migration discipline means you can always roll forward.

---

## What I need from you before we build

We've done "think first." Here's where I've overridden or reshaped your proposal, and the few things I want your sign-off on before we lock **scope → stack → architecture → schema → milestones**:

1. **Scope:** Do you accept the three-tier cut, with **MDS (spine) by ~week 8** as the real safety line and **import + style + beliefs + one tool** as the graded target? This is the single most important agreement.
2. **The import reframe:** Are you OK making **explicit consent + demoing on your own/consented data** a hard requirement, and presenting it as "persona initialization," not "cloning a real person"? (Strongly recommended — it de-risks the ethics review at no technical cost.)
3. **Stack:** Comfortable with **Python + FastAPI + pywebview + SQLite/FTS5/NumPy-vectors + Ollama**, and choosing **React vs HTMX** for the UI based on your JS comfort? (Which is it?)
4. **The structural cuts:** merging **AttentionItem into OpenThread**, deriving **DUE** instead of storing it, and coarse **belief confidence labels** instead of numeric scores — any objections?

Answer those and I'll produce the concrete **SQLite schema + module boundaries + the M0/M1 build** so we start the spine on the right foundation.
