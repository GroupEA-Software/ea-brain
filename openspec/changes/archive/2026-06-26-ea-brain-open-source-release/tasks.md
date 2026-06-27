# Tasks: EA-Brain Open-Source Release

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (all 4 phases) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full rename + branding | PR 1 | base=main; 4 phases sequential |

## Phase 1: License + Docs

- [x] 1.1 Create `LICENSE` — verbatim AGPL v3 (FSF-approved)
- [x] 1.2 Create `README.md` — English install/build/run + AGPL notice
- [x] 1.3 Modify `.gitignore` — add `brain/`, debug/test patterns

## Phase 2: Assistant Rename

- [x] 2.1 Modify `backend/rag.py` — Jarvis→EAgis in system prompts (L1,L341,L366,L412,L593)
- [x] 2.2 Modify `backend/evolution.py` — `'Jarvis'`→`'EAgis'` in conversation label (L226)
- [x] 2.3 Modify `frontend/src/components/Chat.jsx` — Jeeves→EAgis (L122,L136,L190)
- [x] 2.4 Modify `frontend/src/components/Personality.jsx` — Jarvis→EAgis (L65,L118,L234)

## Phase 3: Service Migration

- [x] 3.1 Rename `deploy/baul.service` → `deploy/ea-brain.service` — update description, paths, user
- [x] 3.2 Modify `deploy/setup.sh` — SERVICE_NAME, user, paths, nginx alias, old-service migration
- [x] 3.3 Modify `deploy/README.md` — update all references, paths, commands

## Phase 4: UI Branding + Scripts

- [x] 4.1 Modify `frontend/index.html` — `<title>` "EA-Brain — Digital Brain"
- [x] 4.2 Modify `frontend/package.json` — `"name": "ea-brain-frontend"`
- [x] 4.3 Modify `frontend/src/components/DesktopSidebar.jsx` — branding (L23-L24)
- [x] 4.4 Modify `frontend/src/components/Sidebar.jsx` — branding (L22-L23)
- [x] 4.5 Modify `frontend/src/components/BottomNav.jsx` — **no branding text found; skipped (N/A)**
- [x] 4.6 Modify `frontend/src/api.js` — comment "Jarvis state"→"EAgis state" (L191)
- [x] 4.7 Modify `start.ps1` — banner "EA-Brain — Digital Brain"
- [x] 4.8 Modify `portable.ps1` — same banner update
- [x] 4.9 Modify `fix.ps1` — same banner update
- [x] 4.10 Modify `.env` — comment "EA-Brain Configuration" (L1)
- [x] 4.11 Modify `.atl/skill-registry.md` — title "Skill Registry — EA-Brain" (L1)

## Verification

- [x] V.1 `grep -ri "Jarvis" --include="*.py" --include="*.jsx" --include="*.sh"` → 0 matches (also checked Jeeves — 0 matches)
- [x] V.2 `cd frontend && npm run build` → success (vite build, 393ms)
- [x] V.3 `git status` → **cannot verify — no .git repository exists** (.gitignore changes are in place, N/A)
