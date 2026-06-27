# Design: EA-Brain Open-Source Release

## Technical Approach

Pure rename/branding — 4 sequential phases, each independently revertible. Zero functional changes. Internal code identifiers ("baul" in variable names, logger names, paths) stay untouched — only **external-facing surface** changes.

```
Phase 1 (docs)  ─→ Phase 2 (assistant) ─→ Phase 3 (service) ─→ Phase 4 (UI + scripts)
     │                  │                       │                       │
     └─── no runtime    └─── system prompts      └─── systemd + nginx   └─── npm build test
     └─── .gitignore         + personality             + user migration
```

## Architecture Decisions

### Decision: Internal vs. external naming

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Rename ALL "baul" refs | Churn in 20+ files, risk of breaking internal paths, logger names, config keys | **REJECTED** |
| Rename only external-facing surface | Clean diff, zero functional risk, internal consistency intact | **SELECTED** |

Rationale: `BRAIN_NOTES = BRAIN_PATH / "baul"` (config.py), `logger = logging.getLogger("baul.evolution")`, `localStorage key 'baul_chat_history'` — these are implementation details. Renaming them adds risk with zero external value.

### Decision: Service migration strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| In-place modify baul.service | Breaks existing systems on git pull, no clean rollback | **REJECTED** |
| setup.sh detects old service + migrates | Idempotent, reversible, clean install path | **SELECTED** |

setup.sh will: (1) check `systemctl is-active baul.service`, (2) if active: stop, disable, remove old unit, (3) install `ea-brain.service` with `/opt/ea-brain` paths, (4) create `ea-brain` user, (5) migrate nginx alias, (6) start new service.

### Decision: Assistant rename scope

| Option | Tradeoff | Decision |
|--------|----------|----------|
| sed --in-place on all files | Fast but can corrupt prompts, misses context-dependent refs | **REJECTED** |
| Manual per-file targeting + grep verification | Precise, verifiable, zero risk of prompt corruption | **SELECTED** |

Targeted replacements in system prompt strings (rag.py), conversation labels (evolution.py), and UI descriptions (Chat.jsx, Personality.jsx). Post-rename grep confirms zero Jarvis matches in tracked source files.

### Decision: Data protection

| Option | Tradeoff | Decision |
|--------|----------|----------|
| .gitignore `brain/` only | Catches all notes, but `brain/baul/` is the key concern | **SELECTED** |
| Selective gitignore per subdir | More granular but complex, risk of missing something | **REJECTED** |

`brain/` at root level catches everything: notes, vectors, images, inbox. `.env` already excluded. Post-rename verification step greps for API keys in tracked files.

## File Changes

### Phase 1 — License + Docs (Create)

| File | Action | Description |
|------|--------|-------------|
| `LICENSE` | **Create** | Verbatim AGPL v3 (FSF-approved text) |
| `README.md` | **Create** | English: install, build, run, AGPL notice |
| `.gitignore` | **Modify** | Add `brain/` (entire tree), ensure debug/test patterns |

### Phase 2 — Assistant Rename (Modify)

| File | Lines | Change |
|------|-------|--------|
| `backend/rag.py` | L1,L341,L366,L412,L593 | Jarvis→EAgis, "Baul — el Cerebro Digital"→"EA-Brain — Digital Brain" |
| `backend/evolution.py` | L226 | `'Jarvis'`→`'EAgis'` in conversation label |
| `frontend/src/components/Chat.jsx` | L122,L136,L190 | Jeeves→EAgis in descriptions, placeholder |
| `frontend/src/components/Personality.jsx` | L65,L118,L234 | Jarvis→EAgis in headings, descriptions |

### Phase 3 — Service Migration (Modify + Rename)

| File | Action | Description |
|------|--------|-------------|
| `deploy/baul.service` | **Rename→** `deploy/ea-brain.service` | Update paths, user, description |
| `deploy/setup.sh` | **Modify** | SERVICE_NAME, user, paths, nginx, migration logic |
| `deploy/README.md` | **Modify** | All Baul→EA-Brain, paths, commands |

### Phase 4 — UI + Scripts Branding (Modify)

| File | Change |
|------|--------|
| `frontend/index.html` | `<title>` "Baul — Super Cerebro"→"EA-Brain — Digital Brain" |
| `frontend/package.json` | `"name": "baul-frontend"`→`"ea-brain-frontend"` |
| `frontend/src/components/DesktopSidebar.jsx` | L23-L24: "Baul / Super Cerebro"→"EA-Brain / Digital Brain" |
| `frontend/src/components/Sidebar.jsx` | L22-L23: same change |
| `frontend/src/api.js` | L191 comment: "Jarvis state"→"EAgis state" |
| `start.ps1` | Banner "Baul - Super Cerebro v1.0"→"EA-Brain - Digital Brain" |
| `portable.ps1` | Same banner update |
| `fix.ps1` | Same banner update |
| `.env` | L1 comment: "Baul Configuration"→"EA-Brain Configuration" |
| `.atl/skill-registry.md` | L1 title: "Skill Registry — Baul"→"Skill Registry — EA-Brain" |

**NOT modified** (internal): `backend/config.py` (BRAIN_NOTES path), `backend/main.py` (print labels), `backend/agents.py`, `backend/routes/`, `frontend/src/main.jsx`, CSS files, `requirements.txt`.

## Migration Strategy

```
Production state: baul.service active at /opt/baul

  1. sudo bash deploy/setup.sh          # detects old service
  2.   └─ systemctl stop baul
  3.   └─ systemctl disable baul
  4.   └─ useradd -r ea-brain
  5.   └─ chown -R ea-brain:ea-brain /opt/ea-brain
  6.   └─ install /etc/systemd/system/ea-brain.service
  7.   └─ update nginx alias → /opt/ea-brain
  8.   └─ systemctl enable --now ea-brain

Fresh install: skips steps 2-3, creates ea-brain user, installs service directly.
```

## Testing Strategy

No test infrastructure exists (config.yaml confirms `testing.available: false`). Verification is post-change only:

| Layer | What | How |
|-------|------|-----|
| **Zero remnants** | jarvis grep | `grep -ri "jarvis" --include="*.py" --include="*.jsx" --include="*.sh"` → 0 matches |
| **Build** | Frontend | `cd frontend && npm run build` → success |
| **Git status** | Data protection | `git status` → no `brain/` or `.env` files |
| **Visual** | UI branding | Render each view: sidebar, chat, personality, title bar |
| **Service** | systemd | `systemctl cat ea-brain.service` → correct paths |

## Rollback

| Phase | Rollback command |
|-------|-----------------|
| 1 | `git checkout -- LICENSE README.md .gitignore` |
| 2 | `git checkout -- backend/rag.py backend/evolution.py frontend/src/components/Chat.jsx Personality.jsx` |
| 3 | `systemctl stop ea-brain; systemctl enable baul --now` + restore nginx alias |
| 4 | `git checkout -- frontend/index.html frontend/package.json DesktopSidebar.jsx Sidebar.jsx api.js *.ps1 .env` |

No migration required for existing data — brain notes path (`brain/baul/`) stays unchanged.

## Open Questions

None — all decisions resolved in proposal + spec.
