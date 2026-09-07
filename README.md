# HelloSienna — M0 (foundation)

Local-first persistent AI companion for Windows. **This is the M0 milestone only**:
it proves the skeleton is wired end to end. It contains **no** memory, retrieval,
persona, attention, tools, or persistence of conversations — those arrive in M1+.

## Architecture (frozen v1)
- **Core language:** Python. **UI:** React + TypeScript. **Shell:** pywebview + FastAPI on `127.0.0.1`.
- **Invariant:** the UI never imports cognition code; it talks only to the localhost API.
- **Storage:** SQLite (single source of truth). Private data lives under `%LOCALAPPDATA%\HelloSienna` — never in this repo.
- **Auth:** a per-launch token sent only as the `X-HS-Token` header (never in a URL/log/persisted state).

## Run (Windows target)
```
# backend
cd backend
pip install -e .
python -m hellosienna.main        # launches server + pywebview window
# requires Ollama running for live chat: https://ollama.com  (pull the chat model first)
```
The frontend is built into `frontend/dist` and served by the backend:
```
cd frontend
npm install
npm run build
```

## Test / verify
```
cd backend && pytest                 # backend unit + integration
cd frontend && npm run test          # API client (SSE parse + header-only token)
cd frontend && npm run build         # type-check + production build
```

## Layout
See the Pre-M0 Implementation Contract (project record). Packages are created at the
milestone they belong to — `core/` currently holds only the Clock abstraction.
