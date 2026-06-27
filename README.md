# EA-Brain — Digital Brain

> Your second brain. A personal AI-powered knowledge management system with a RAG engine, Markdown notes, vector search, and an evolving digital butler.

EA-Brain is a full-stack application that combines a React frontend with a Python/FastAPI backend. It organizes your notes, knowledge library, and personal data — all stored locally in Markdown — with AI-powered search, connections, and a personality-driven assistant (EAgis) to help you interact with your digital brain.

**Everything stays on your machine.** Your notes, vectors, files, and configuration never leave your local environment unless you explicitly deploy or sync them. Each installation is independent and self-contained.

---

## Features

- **📝 Markdown Notes** — Create, edit, search, and organize notes in folders
- **🧠 RAG Engine** — AI-powered retrieval-augmented generation using DeepSeek, Groq, or Gemini
- **📝 Quiz Generator** — Generates large multiple-choice quizzes (100+ questions) from your brain content, split into chunks for reliability. Download as `.md` or `.pdf`
- **🕸️ Knowledge Graph** — Automatic discovery of connections between notes
- **🎭 Evolving AI Assistant** — EAgis, your digital butler with an evolving personality
- **📚 Knowledge Library** — Categorized reference material
- **📥 Smart Inbox** — Upload and convert files (images, audio, PDFs, documents) into notes
- **🔄 Repo Sync** — Connect external repositories and sync content
- **🌐 Web Search** — Search the web when your brain doesn't have the answer
- **📦 Portable Mode** — Run locally or expose via Cloudflare Tunnel

---

## Requirements

- **Python 3.10+**
- **Node.js 18+**
- **npm 9+**

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/GroupEA-Software/EA-Brain.git
cd ea-brain
```

### 2. Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Configure

Create a `.env` file in the project root (the app will look for it automatically):

```bash
# At minimum, set one API key:
#   OPENCODE_API_KEY (free: https://opencode.ai/zen)
#   GROQ_API_KEY     (free: https://console.groq.com)
#   GEMINI_API_KEY   (free: https://aistudio.google.com)
```

A template with all available options is at `deploy/.env.production`.

### 5. Run

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 3000
```

Then open **http://localhost:3000** in your browser.

The `brain/` directory is created automatically on first run — you don't need to set it up manually.

---

## Data Model (important)

EA-Brain is **local-first**. All your data lives in a single folder:

```txt
ea-brain/
├── brain/                ← YOUR DATA — everything you create
│   ├── baul/
│   │   ├── notes/        ← Your Markdown notes
│   │   ├── vectors/      ← Vector embeddings for RAG search
│   │   └── graph/        ← Knowledge graph state
│   ├── inbox/            ← Uploaded files (images, PDFs, audio) pending conversion
│   └── archive/          ← Processed inbox items
├── .env                  ← Your API keys and configuration
└── ...                   ← App source code (backend/, frontend/, deploy/)
```

| What | Where | Back it up? |
|------|-------|-------------|
| Notes, vectors, knowledge graph | `brain/` | ✅ Yes — this is your data |
| API keys, config | `.env` | ✅ Yes, but keep it secret |
| App source code | `backend/`, `frontend/` | ❌ No — just clone again |
| Vector search index | `brain/baul/vectors/` | Regenerated from notes if lost |

### Moving to another machine

Your data is completely portable:

```bash
# On the old machine
cp -r brain/ brain-backup/

# On the new machine (after cloning the repo)
cp -r brain-backup/ ea-brain/brain/
```

Start the app and everything is there — notes, graph, vectors, everything.

---

## Project Structure

```
ea-brain/
├── backend/          # Python/FastAPI backend
│   ├── main.py       # FastAPI app entry point
│   ├── rag.py        # RAG engine + EAgis personality
│   ├── evolution.py  # Autonomous learning & connections
│   └── ...
├── frontend/         # React + Vite frontend
│   ├── src/          # React components
│   └── ...
├── deploy/           # Production deployment scripts
├── LICENSE           # GNU AGPL v3
└── README.md         # This file
```

Data directories (`brain/`, `.env`) are created at runtime and excluded from version control.

---

## API Keys

EA-Brain works with multiple AI backends, tried in order:

| Service | Cost | Key needed? | Setup |
|---------|------|-------------|-------|
| **OpenCode Zen** | Free | No (recommended default) | Just leave `OPENCODE_API_KEY` empty |
| **Groq** | Free | Yes | Sign up at https://console.groq.com |
| **Gemini** | Free | Yes | Get key at https://aistudio.google.com |
| **Ollama** (local) | Free | No | Install Ollama, pull a model, uncomment in `.env` |

No API key is required to start — OpenCode Zen works out of the box with open-source models.

---

## Production Deployment

See [deploy/README.md](deploy/README.md) for Debian/Ubuntu server setup with systemd, nginx, and service management.

```bash
sudo bash deploy/setup.sh
```

---

## License

**EA-Brain — Digital Brain**  
Copyright (C) 2026 GroupEA-Software

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU Affero General Public License** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU AGPL v3](LICENSE) for details.

---

*Built by [GroupEA-Software](https://github.com/GroupEA-Software)*
