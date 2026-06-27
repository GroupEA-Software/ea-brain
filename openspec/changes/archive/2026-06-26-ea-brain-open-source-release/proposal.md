# Proposal: EA-Brain Open-Source Release

## Intent

Prepare Baul — Super Cerebro for public release as EA-Brain under AGPL v3. Rename all external-facing references (branding, assistant, service name, UI), add license/README, and protect personal data before publishing to GitHub.

## Scope

### In Scope
- AGPL v3 LICENSE + .gitignore (exclude `brain/`, `.env`, debug files) + English README
- Rename assistant Jarvis → EAgis (system prompts, UI description)
- Service rename `baul.service` → `ea-brain.service` with migration script
- Frontend branding: title, sidebar, descriptions, `package.json` name
- Scripts (.ps1), `.env` comments, `.atl/skill-registry.md`, `openspec/config.yaml`

### Out of Scope
- PostgreSQL migration (separate phase)
- Multi-user implementation (schema only, deferred)
- Internal "baul" references in code (logs, variables, routes)
- Rename `brain/baul/` directory
- GitHub repo creation and push
- Test infrastructure

## Capabilities

### New Capabilities
None — branding/rename only, no new features.

### Modified Capabilities
None — no spec-level behavior changes.

## Approach

Four phases, sequential:
1. **License + docs**: `LICENSE`, `.gitignore`, `README.md`
2. **Assistant rename**: Jarvis → EAgis in `backend/rag.py`, `backend/evolution.py`, `frontend/src/components/Chat.jsx`, `Personality.jsx`, `DesktopSidebar.jsx`
3. **Service migration**: `deploy/setup.sh` (SERVICE_NAME, BAUL_USER, paths, nginx alias, migration from old baul.service), `deploy/baul.service` → `ea-brain.service` (description, paths)
4. **Frontend + scripts**: titles, sidebar text, `package.json`, `.ps1` banners, `.env` comments, config files

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/rag.py` | Modified | System prompts: Jarvis → EAgis |
| `backend/evolution.py` | Modified | System prompts: Jarvis → EAgis |
| `frontend/src/components/Chat.jsx` | Modified | "Jeeves, tu mayordomo digital" |
| `frontend/src/components/Personality.jsx` | Modified | Jarvis refs → EAgis |
| `frontend/src/components/DesktopSidebar.jsx` | Modified | Branding text |
| `frontend/src/components/BottomNav.jsx` | Modified | Branding text |
| `frontend/src/components/Sidebar.jsx` | Modified | Branding text |
| `frontend/index.html` | Modified | `<title>` |
| `frontend/package.json` | Modified | `name` field |
| `frontend/src/api.js` | Modified | Comment refs |
| `deploy/setup.sh` | Modified | SERVICE_NAME, BAUL_USER, migration |
| `deploy/baul.service` | Modified | → `ea-brain.service` |
| `deploy/README.md` | Modified | References update |
| `LICENSE` | New | AGPL v3 |
| `.gitignore` | Modified | Exclude brain/, .env, debug |
| `README.md` | New | English GitHub README |
| `*.ps1` | Modified | Banners, references |
| `.env` | Modified | Comment update |
| `.atl/skill-registry.md` | Modified | Title update |
| `openspec/config.yaml` | Modified | Already documents rename |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Service rename breaks existing deploy | Medium | Migration check in setup.sh detects old `baul.service` and migrates |
| Personal data exposure | Low | `.gitignore` excludes `brain/` entirely |
| EAgis name renders poorly in UI | Low | Visual check after change |

## Rollback Plan

1. Revert all file changes with `git checkout -- .` (staged before public push)
2. If service renamed, setup.sh migration is reversible: `systemctl stop ea-brain && systemctl enable baul --now`
3. `.gitignore` additions are additive — no rollback needed

## Dependencies

- `AGENTS.md` and `GEMINI.md` in project root (rename assistant refs if present)
- Existing `baul.service` on production for migration path

## Success Criteria

- [ ] `git status` shows no unexpected files (brain/ excluded)
- [ ] `grep -r "Jarvis" --include="*.py" --include="*.jsx" --include="*.sh"` returns zero matches
- [ ] `npm run build` succeeds for frontend
- [ ] README is valid English with install/build/run instructions
- [ ] LICENSE is verbatim AGPL v3 (FSF-approved)
