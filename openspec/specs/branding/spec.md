# Delta Spec: EA-Brain Open-Source Release

No new or modified capabilities — branding/rename/infra only. These are new spec domains.

## Branding

### ADDED Requirements

**Requirement: Frontend displays EA-Branding**

The frontend MUST show "EA-Brain" and "Digital Brain" instead of "Baul" and "Super Cerebro" in all visible UI text.

- GIVEN the frontend is loaded
- WHEN the user navigates sidebar, bottom nav, or page title
- THEN branding reads "EA-Brain — Digital Brain"
- AND no "Baul" or "Super Cerebro" appears in visible UI
- AND `<title>` MUST be "EA-Brain"

**Requirement: package.json identity**

`frontend/package.json` `name` MUST be `"ea-brain-frontend"`.

- GIVEN `frontend/package.json`
- WHEN the `name` field is inspected
- THEN it MUST equal `"ea-brain-frontend"`

## Assistant (Jarvis → EAgis)

### ADDED Requirements

**Requirement: System prompts use EAgis**

`backend/rag.py` and `backend/evolution.py` system prompts MUST name "EAgis" instead of "Jarvis".

- GIVEN both backend files
- WHEN system prompt strings are read
- THEN they MUST refer to "EAgis"

**Requirement: UI descriptions use EAgis**

Frontend assistant descriptions in `Chat.jsx` and `Personality.jsx` MUST say "EAgis" — not "Jarvis" or "Jeeves".

- GIVEN the frontend renders assistant text
- WHEN the description is inspected
- THEN it MUST say "EAgis"

**Requirement: No Jarvis remnants**

Tracked source files MUST contain zero matches for "Jarvis" after rename.

- GIVEN all tracked `.py`, `.jsx`, `.sh` files
- WHEN searched for "Jarvis"
- THEN zero matches MUST be found

## Service-Infra

### ADDED Requirements

**Requirement: Service migration path**

Deploy MUST migrate from `baul.service` to `ea-brain.service` with automatic detection.

- GIVEN `baul.service` exists and is active
- WHEN `deploy/setup.sh` runs
- THEN it MUST stop/disable `baul.service`
- AND enable/start `ea-brain.service`
- AND create user `ea-brain` (or migrate from `baul`)

- GIVEN no existing `baul.service`
- WHEN `deploy/setup.sh` runs
- THEN it MUST install `ea-brain.service` directly

**Requirement: Nginx alias updated**

Nginx alias MUST point to `/opt/ea-brain`.

- GIVEN `deploy/setup.sh` configures nginx
- WHEN the alias is set
- THEN it MUST be `/opt/ea-brain`

## Open-Source

### ADDED Requirements

**Requirement: AGPL v3 LICENSE**

Project root MUST contain verbatim AGPL v3 license (FSF-approved text).

- GIVEN the repository root
- WHEN `LICENSE` is read
- THEN it MUST contain standard AGPL v3 preamble

**Requirement: English README**

An English `README.md` MUST document install, build, and run steps.

- GIVEN `README.md`
- WHEN a new developer reads it
- THEN it MUST explain setup, build, and execution

**Requirement: .gitignore exclusions**

`.gitignore` MUST exclude `brain/`, `.env`, and debug/temp files.

- GIVEN `brain/baul/` has personal notes
- WHEN `git status` runs
- THEN no `brain/` files appear as untracked

- GIVEN `.env` has secrets
- WHEN `git status` runs
- THEN `.env` MUST NOT appear as untracked

## Data-Protection

### ADDED Requirements

**Requirement: No personal data in public repo**

ZERO personal notes, secrets, or identifiable data MUST reach GitHub.

- GIVEN `.gitignore` excludes `brain/`
- WHEN files are added under `brain/baul/notes/`
- THEN `git status` SHALL NOT show them

- GIVEN the public repository is inspected
- WHEN tracked files are grepped for API keys or personal identifiers
- THEN no secrets SHALL be found
