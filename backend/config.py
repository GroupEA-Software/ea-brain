import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Ensure backend directory is on path for sibling imports
_backend_dir = Path(__file__).parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
BRAIN_PATH = Path(os.getenv("BRAIN_PATH", BASE_DIR / "brain"))

BRAIN_NOTES = BRAIN_PATH / "baul"
BRAIN_INBOX = BRAIN_PATH / "inbox"
BRAIN_CONNECTIONS = BRAIN_PATH / "connections"
BRAIN_META = BRAIN_PATH / "meta"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Groq (free Llama 3 via API, sign up at https://console.groq.com)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Ollama (local Llama 3, no API key needed)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Gemini (Google AI, for audio transcription and chat)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# OpenCode Zen (open-source AI agent gateway, free tier available)
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash-free")
OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"

# Personality evolution state
PERSONALITY_PATH = BRAIN_META / "personality.json"

CONNECTOR_THRESHOLD = float(os.getenv("CONNECTOR_THRESHOLD", "0.30"))
CONNECTOR_INTERVAL = int(os.getenv("CONNECTOR_INTERVAL", "1800"))
EVOLVER_INTERVAL = int(os.getenv("EVOLVER_INTERVAL", "3600"))

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_DIM = 384

# Directorios de conocimiento (01-07) — contenido de Cerebro-Digital
KNOWLEDGE_DIRS = {
    "01 - Fundamentos de Ingeniería": BASE_DIR / "01 - Fundamentos de Ingeniería",
    "02 - Lenguajes y Frameworks": BASE_DIR / "02 - Lenguajes y Frameworks",
    "03 - Sistemas Low Level y Seguridad": BASE_DIR / "03 - Sistemas, Low Level y Seguridad",
    "04 - Carrera y Seniority": BASE_DIR / "04 - Carrera y Seniority (Soft Skills)",
    "05 - Inteligencia Artificial": BASE_DIR / "05 - Inteligencia Artificial (IA)",
    "06 - Experiencia y Fuentes": BASE_DIR / "06 - Experiencia y Fuentes",
    "07 - Materias": BASE_DIR / "07 - materias",
}

for d in [BRAIN_NOTES, BRAIN_INBOX, BRAIN_CONNECTIONS, BRAIN_META]:
    d.mkdir(parents=True, exist_ok=True)

# Migrate existing notes from old "notes" dir to "baul"
_old_notes = BRAIN_PATH / "notes"
if _old_notes.is_dir() and _old_notes != BRAIN_NOTES:
    try:
        import shutil
        for f in _old_notes.rglob("*"):
            if f.is_file():
                rel = f.relative_to(_old_notes)
                dest = BRAIN_NOTES / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(f, dest)
        shutil.rmtree(_old_notes)
        print("[Baul] Migrated notes from 'notes' to 'baul' directory.")
    except Exception as e:
        print(f"[Baul] Migration warning: {e}")
