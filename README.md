# EA-Brain — Digital Brain

> Your second brain. A personal AI-powered knowledge management system with a RAG engine, Markdown notes, vector search, and an evolving digital butler.

EA-Brain (formerly "Baul — Super Cerebro") is a full-stack application that combines a React frontend with a Python/FastAPI backend. It organizes your notes, knowledge library, and personal data — all stored locally in Markdown — with AI-powered search, connections, and a personality-driven assistant (EAgis) to help you interact with your digital brain.

---

## Features

- **📝 Markdown Notes** — Create, edit, search, and organize notes in folders
- **🧠 RAG Engine** — AI-powered retrieval-augmented generation using DeepSeek, Groq, or Gemini
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
git clone <repo-url> ea-brain
cd ea-brain
```

### 2. Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Configure

Copy or edit `.env` (a template is created automatically on first run):

```bash
# At minimum, set one API key:
#   OPENCODE_API_KEY (free: https://opencode.ai/zen)
#   GROQ_API_KEY     (free: https://console.groq.com)
#   GEMINI_API_KEY   (free: https://aistudio.google.com)
```

### 5. Run

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 3000
```

Then open http://localhost:3000 in your browser.

On **Windows**, you can also use:

```powershell
.\start.ps1        # Starts backend + builds frontend
.\portable.ps1     # Portable mode with Cloudflare Tunnel
```

---

## Project Structure

```
ea-brain/
├── backend/          # Python/FastAPI backend
│   ├── main.py       # FastAPI app entry point
│   ├── rag.py        # RAG engine + EAgis personality
│   ├── evolution.py  # Autonomous learning & connections
│   ├── config.py     # Configuration & paths
│   └── ...
├── frontend/         # React + Vite frontend
│   ├── src/          # React components
│   └── ...
├── brain/            # Your personal data (excluded from version control)
│   ├── baul/         # Markdown notes
│   ├── inbox/        # Uploaded files pending conversion
│   └── ...
├── deploy/           # Production deployment scripts
├── .env              # Configuration (API keys, paths)
├── LICENSE           # GNU AGPL v3
└── README.md         # This file
```

---

## API Keys

EA-Brain works with multiple AI backends, tried in order:

| Service | Cost | Setup |
|---------|------|-------|
| **OpenCode Zen** | Free | Get key at https://opencode.ai/zen |
| **Groq** | Free | Sign up at https://console.groq.com |
| **Gemini** | Free | Get key at https://aistudio.google.com |
| **Ollama** (local) | Free | Install Ollama, pull a model, uncomment in `.env` |

---

## Production Deployment

See [deploy/README.md](deploy/README.md) for Debian/Ubuntu server setup with systemd, nginx, PostgreSQL, and automatic service migration.

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
