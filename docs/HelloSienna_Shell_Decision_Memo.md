# HelloSienna — Desktop Shell Decision Memo

**Question:** pywebview + Python/FastAPI + React  **vs**  Tauri + React + packaged Python sidecar, for HelloSienna on Windows.
**Decision rule:** lowest *total* project risk across the full major-project lifecycle (not "most modern," not "simplest").
**Recommendation:** **Option 1 — pywebview + FastAPI (127.0.0.1) + React/TypeScript.** Adopt it for M0. Keep Tauri as a documented, low-cost escape hatch, made cheap by the FastAPI/localhost seam.

---

## The one insight that decides it

HelloSienna's hard requirement is **a Python cognition process + proactive scheduler that stays alive while the main window is hidden.** That reshapes the comparison:

- **pywebview:** Python is the *root* process; the webview is a child GUI. Hide the window and Python + uvicorn + APScheduler keep running by default. The requirement is satisfied by the process model itself.
- **Tauri:** Rust is the root; Python is a *managed sidecar*. To meet the same requirement you must write Rust to (a) keep the app running on window-close, (b) hide to tray, (c) keep the sidecar alive, and (d) re-spawn it on crash — in a language you don't know, near a deadline.

Everything Tauri is better at (installer, tray, notifications, auto-update) is real but sits in the *last 10% of polish*. Everything pywebview is better at attacks the *top completion risks* for a solo Python dev on 3–4 months: single-runtime debugging, trivial process liveness, simple packaging, and reversibility. Polish doesn't move an undergrad grade the way a packaging/lifecycle bug in an unfamiliar language can sink the project.

---

## Criterion-by-criterion (only what matters to HelloSienna)

| Criterion | pywebview + FastAPI + React | Tauri + React + Python sidecar | Edge |
|---|---|---|---|
| React integration | Serve built React (or Vite dev server) into a WebView2 window | Same, slightly nicer scaffolding/HMR | ≈ (tiny Tauri) |
| Python IPC | React ↔ FastAPI over localhost HTTP/WS — one hop, standard, you own it | Cleanest is *also* React ↔ localhost-Python (Rust not in data path); the Rust↔Python stdio bridge is a worse second hop | **pywebview** |
| Streaming chat | SSE/WebSocket from FastAPI — clean | Clean *if* using the localhost-server pattern; poor over stdio bridge | **pywebview** |
| System tray | `pystray` + main-thread coordination (works, fiddlier) | Native plugin, robust | **Tauri** |
| Windows notifications | `winotify`/WebView2 HTML notifications | Native notification plugin | **Tauri** (minor) |
| Minimize-to-tray | Hide window + pystray icon | `close → hide`, native | **Tauri** (minor) |
| Start-on-login | Registry `Run` key / Startup shortcut (few lines) | Autostart plugin | **Tauri** (marginal; pywebview version is trivial) |
| **Keep Python alive while window hidden** | Natural — Python is the root process | Must be engineered in Rust (prevent-exit + sidecar keep-alive + respawn) | **pywebview (major)** |
| **Proactive scheduler reliability** | Tied to a root Python process staying alive → simplest | Tied to correct sidecar lifecycle in Rust | **pywebview (major)** |
| WebView2 behavior/dependency | Same WebView2 runtime dep (present on Win11 / updated Win10) | Same dep; handling slightly more battle-tested | ≈ (tiny Tauri) |
| PyInstaller interaction | Freeze the whole app as one Python artifact — well-trodden | Freeze Python sidecar **and** bundle in Tauri **and** cargo build — more coupling, more failure modes | **pywebview** |
| Installer / distribution | Assemble with Inno Setup/NSIS yourself; larger bundle | MSI/NSIS + updater + signing out of the box | **Tauri (clear)** |
| Dev / debugging complexity | One runtime you know (Python) + React | Rust **and** Python **and** React — two unfamiliar toolchains | **pywebview (major)** |
| Final app polish | Good, but heavier/less native | Smaller, snappier, auto-update, native chrome | **Tauri** |
| Migration cost if shell becomes limiting | Low — the localhost seam lets you swap the shell only | Low too, but the upfront Rust cost is already sunk | **pywebview** |

**Net:** Tauri wins the polish/distribution/native-integration cluster; pywebview wins the risk-dominant cluster (IPC simplicity, process liveness, scheduler reliability, packaging simplicity, single-runtime debugging, reversibility). For *lowest total lifecycle risk on this project*, pywebview wins.

---

## Challenge: does pywebview actually need FastAPI/localhost, or is a bare Python↔webview bridge simpler?

**Keep FastAPI on `127.0.0.1`. The bare `js_api` bridge is the wrong tool here, for four concrete reasons:**

1. **Streaming.** pywebview's `js_api` is request/response. Streaming chat tokens over it means Python calling `window.evaluate_js(...)` per token — string-eval'ing into JS, clumsy and fragile. FastAPI + SSE/WebSocket streams tokens the standard way React already understands.
2. **Server-initiated pushes.** The proactive scheduler must push a message *into* the UI unprompted. That's a natural WebSocket event from FastAPI; over `js_api` it's another `evaluate_js` hack.
3. **The evaluation harness (graded).** A localhost API means your probe-set experiments and attention/timeline tests hit real endpoints from plain Python scripts — no GUI in the loop. That's a large, free win for Section J.
4. **Reversibility (the decisive one).** With the FastAPI/localhost seam, the *real app is FastAPI + React* and **pywebview is just one possible window around it.** The shell becomes almost disposable. This is precisely what makes migrating to Tauri later cheap.

Cost of FastAPI is ~one uvicorn server on a random free loopback port started in a daemon thread before `webview.start()`. Bind to `127.0.0.1` only; add a per-launch token/localhost-origin check so nothing else on the machine can talk to the cognition API. Small cost, large structural payoff.

## For the record: the cleanest Tauri↔Python boundary (if we ever migrate)

Do **not** route conversation data through Rust. Rust's job is lifecycle only: on launch, spawn the PyInstaller-frozen Python binary as a Tauri **sidecar** bound to `127.0.0.1:<port>`; own the tray, notifications, autostart, and window; keep the sidecar alive and respawn on crash; kill it on true quit. **React talks directly to the Python FastAPI server over localhost HTTP/WS for all data (including streaming).** stdio JSON between Rust and Python is reserved for lifecycle/health signals only. Because this reuses the exact FastAPI + React we build now, a future migration rewrites the *shell*, not the app — an estimated few days, not a rebuild.

---

## Decision & consequences

- **Adopt Option 1 (pywebview + FastAPI + React/TS) for M0.**
- Architecture invariant: **the UI never imports cognition code; it only calls the localhost API.** This is what keeps the shell replaceable.
- pywebview's genuine weak spots — tray + main-thread coordination, native toasts — are bounded, well-documented Python problems (`pystray`, `winotify`), scheduled into M3 where tray/notifications already live.
- **Trigger to revisit Tauri:** if, at ~M7, installer polish / code-signing / auto-update becomes a graded or distribution requirement, migrate the shell only, reusing FastAPI + React unchanged. Until then, Rust adds risk without moving the grade.

**This unblocks freezing Architecture v1 and starting M0.**
