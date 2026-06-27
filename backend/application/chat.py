"""Chat use case — main interaction loop with RAG."""
import re
from backend.domain.models import Personality
from backend.ports.llm import LLMRouter
from backend.ports.repositories import NoteRepository
from backend.ports.search import VectorSearchPort, WebSearchPort
from backend.application.search import SearchService
from backend.application.personality import PersonalityService
from backend.infrastructure.logger import get_logger

logger = get_logger("application.chat")

_QUIZ_PATTERNS = re.compile(
    r"\b(?:quiz|test|examen|cuestionario|preguntame|examiname|"
    r"questionario|preguntas)\b", re.IGNORECASE
)
_NOTE_REQUEST_PATTERNS = re.compile(
    r"\b(?:mostrame|enseñame|dame.*nota|show.*note|open.*note|"
    r"leeme|read.*note|abri|abrime)\b", re.IGNORECASE
)
_COUNT_PATTERN = re.compile(
    r"(\d+)\s*(preguntas?|questions?|items?|reactivos?|ejercicios?|"
    r"puntos?|points?|temas?|topics?|cap[ií]tulos?|chapters?|"
    r"hojas?|pages?|p[aá]ginas?)",
    re.IGNORECASE,
)


class ChatService:
    """Orchestrates the RAG chat interaction."""

    def __init__(self, llm_router: LLMRouter, vector_search: VectorSearchPort,
                 web_search: WebSearchPort | None, note_repo: NoteRepository,
                 personality_svc: PersonalityService):
        self._llm = llm_router
        self._search_svc = SearchService(vector_search, web_search)
        self._notes = note_repo
        self._personality = personality_svc

    async def answer(self, message: str, history: list[dict] | None = None) -> dict:
        """Process a chat message and return the response with metadata."""
        lang = self._detect_language(message)
        personality = await self._personality.load()
        is_quiz = bool(_QUIZ_PATTERNS.search(message)) and not _NOTE_REQUEST_PATTERNS.search(message)
        qty = self._extract_quantity(message)

        # Build prompt
        context = await self._build_context(message)
        system_prompt = self._build_system_prompt(lang, context, personality)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})

        # Generate answer
        max_tokens = 2048 if is_quiz else 1024
        if qty > 0:
            max_tokens = min(2048 + qty * 40, 8000)

        answer = await self._llm.race(
            messages,
            max_tokens=max_tokens,
            timeout=45.0 if qty > 10 else 30.0,
        )

        if not answer:
            answer = self._local_fallback(context, lang, personality)

        # Update personality
        await self._personality.update(message, answer, lang, [])
        personality = await self._personality.load()

        return {
            "answer": answer,
            "sources": [],
            "connections": [],
            "is_quiz": is_quiz,
            "topic": message[:60],
            "personality": {
                "interactions": personality.interactions_count,
                "traits": personality.user_traits[-3:],
                "topics": personality.favorite_topics[:3],
            },
        }

    async def _build_context(self, message: str) -> str:
        """Search brain and build context string."""
        results = await self._search_svc.search_brain(message, k=5)
        if not results:
            return "No hay contenido relevante en el cerebro todavia."

        lines = []
        for r in results[:3]:
            note = await self._notes.get(r.filename)
            if note:
                lines.append(f"## [[{r.filename}]]\n{note.content[:1000]}\n")
        return "\n---\n".join(lines) if lines else "No hay contenido relevante."

    def _build_system_prompt(self, lang: str, context: str,
                             personality: Personality) -> str:
        """Build the EAgis system prompt."""
        traits = ""
        if personality.user_traits:
            traits = "Lo que se del usuario:\n" + "\n".join(
                f"- {t}" for t in personality.user_traits[-5:]
            ) + "\n"
        topics = ""
        if personality.favorite_topics:
            topics = "Temas que le interesan: " + ", ".join(
                personality.favorite_topics[:5]
            ) + ".\n"

        return f"""Eres EAgis, un asistente de IA con personalidad.

{traits}{topics}
CONTEXTO DEL CEREBRO:
{context[:4000]}"""

    def _detect_language(self, text: str) -> str:
        spanish_words = {
            "que", "es", "el", "la", "los", "las", "un", "una", "y", "e", "o",
            "de", "del", "en", "con", "por", "para", "se", "su", "no", "lo",
            "como", "mas", "pero", "sus", "le", "ya", "este", "entre", "porque",
            "cuando", "todo", "tambien", "fue", "era", "muy", "sin", "sobre",
            "ser", "tiene", "son", "dos", "hay", "cada", "parte", "donde",
            "cual", "aqui", "alli", "ahora", "siempre", "nunca", "hacer",
            "tener", "estar", "poder", "saber", "mismo", "otro", "nuestro",
            "ningun", "aunque", "segun", "hola", "gracias", "como", "estas",
            "bien", "mal", "chau", "adios", "bueno", "mala", "cosa", "gente",
            "casa", "vida", "tiempo", "dia", "archivo", "nota", "cerebro",
            "baul", "pregunta", "cuestionario",
        }
        words = set(w.lower().strip(".,!?;:") for w in text.split())
        spanish_count = sum(1 for w in words if w in spanish_words)
        return "es" if spanish_count >= 2 else "en"

    def _extract_quantity(self, text: str) -> int:
        m = _COUNT_PATTERN.search(text)
        if m:
            return max(1, min(int(m.group(1)), 500))
        return 0

    def _local_fallback(self, context: str, lang: str,
                        personality: Personality) -> str:
        notes = re.findall(r"\[\[([^\]]+)\]\]", context)
        notes = list(set(notes))[:5]
        name = "EAgis"
        base = f"*{name} adjusts his tie and clears his throat.*\n"
        base += "Quite. I've consulted the brain archives.\n\n"
        if context.strip():
            base += "**From your notes:**\n"
            for line in context.split("\n")[:5]:
                if line.strip() and len(line) > 20:
                    base += f"- {line.strip()[:200]}\n"
            base += "\n"
        if notes:
            base += "**Relevant entries:**\n"
            base += "\n".join(f'- [[{n}]]' for n in notes) + "\n\n"
        base += "Do feed me some material to work with. I'm dreadfully underutilised."
        return base
