"""
rag.py — EA-Brain RAG engine with evolved EAgis personality.

- Primary LLM: DeepSeek V4 Flash Free via OpenCode Zen
- Personality evolution: reads/writes personality state to brain/meta/
- Quiz/questionnaire mode
- Web search with auto-save suggestions
- Full brain + knowledge library access
"""

import re
import json
import asyncio
from typing import List, Optional
from datetime import datetime

from backend.config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL,
    GEMINI_API_KEY, GEMINI_MODEL,
    OPENCODE_API_KEY, OPENCODE_MODEL, OPENCODE_BASE_URL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    BRAIN_NOTES, KNOWLEDGE_DIRS, PERSONALITY_PATH,
)
from backend.vector_store import search as vector_search


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

_SPANISH_WORDS = {
    "que", "es", "el", "la", "los", "las", "un", "una", "y", "e", "o", "a",
    "de", "del", "en", "con", "por", "para", "se", "su", "no", "lo", "como",
    "mas", "pero", "sus", "le", "ya", "este", "entre", "porque", "cuando",
    "todo", "tambien", "fue", "era", "muy", "sin", "sobre", "ser", "tiene",
    "son", "dos", "hay", "cada", "parte", "donde", "cual", "porque", "sino",
    "aqui", "alli", "ahora", "siempre", "nunca", "hacer", "tener", "estar",
    "poder", "saber", "mismo", "otro", "nuestro", "ningun", "aunque", "segun",
    "hola", "gracias", "como", "estas", "bien", "mal", "chau", "adios",
    "bueno", "mala", "cosa", "gente", "casa", "vida", "tiempo", "dia",
    "archivo", "nota", "cerebro", "baul", "jeeves",
}

_STOPWORDS_ES = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
    "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como",
    "mas", "pero", "sus", "le", "ya", "este", "entre", "porque", "cuando",
    "todo", "tambien", "fue", "era", "muy", "sin", "sobre", "ser", "tiene",
    "son", "dos", "hay", "cada", "parte", "donde", "cual", "este", "ese",
    "esa", "esas", "esos", "ello", "ante", "cabe", "contra", "durante",
    "mediante", "segun", "tras", "etc", "sino", "aqui", "alli", "allá",
    "ahora", "siempre", "nunca", "hace", "hasta", "desde",
}

_MORE_DETAIL_PATTERNS = re.compile(
    r"\b(amplia|ampliar|mas\s*detalle|mas\s*contexto|explica\s+mas|"
    r"desarrolla|profundiza|extiende|expand|more\s*detail|more\s*context|"
    r"elaborate|explain\s+more|give\s+me\s+more|tell\s+me\s+more)\b",
    re.IGNORECASE,
)

_NOTE_REQUEST_PATTERNS = re.compile(
    r"\b(?:muestrame|abre|abrir|lee|leer|que\s*dice|que\s*contiene|"
    r"busca|encuentra|donde\s*esta|como\s*se\s*llama|"
    r"show\s*me|open|read|find|get|fetch|what.*says|where\s*is)\b"
    r".*?(?:nota|archivo|documento|file|note|doc)",
    re.IGNORECASE,
)

_QUIZ_PATTERNS = re.compile(
    r"\b(?:quiz|test|examen|cuestionario|preguntame|examiname|"
    r"questionario|evaluacion|exam|evalua|evaluate|"
    r"hazme\s*preguntas|ponme\s*a\s*prueba|challenge\s*me)\b",
    re.IGNORECASE,
)

_KEYWORD_PATTERNS = re.compile(r"\b[a-zA-Z\u00f1\u00e1-\u00fa]{4,}\b")


# ══════════════════════════════════════════════════════════════════════════════
# NOTE RESOLUTION
# ══════════════════════════════════════════════════════════════════════════════

def _get_note_content(note_name: str) -> Optional[str]:
    """Fetch full content of a note by name (partial or exact).
    
    Handles both brain/baul/ notes and __conocimiento__/ knowledge notes.
    """
    try:
        note_path = BRAIN_NOTES / note_name
        if note_path.exists():
            return note_path.read_text(encoding="utf-8")
        note_path = BRAIN_NOTES / f"{note_name}.md"
        if note_path.exists():
            return note_path.read_text(encoding="utf-8")
        
        for f in sorted(BRAIN_NOTES.rglob("*.md")):
            name_lower = note_name.lower().rstrip(".md")
            if (name_lower in f.stem.lower() or
                name_lower in str(f.relative_to(BRAIN_NOTES)).lower()):
                return f.read_text(encoding="utf-8")

        if note_name.startswith("__conocimiento__/"):
            parts = note_name.replace("\\", "/").split("/", 2)
            if len(parts) >= 3:
                cat_part = parts[1]
                file_path = parts[2]
                for cat_name, cat_dir in KNOWLEDGE_DIRS.items():
                    cn = cat_name.lower().strip().replace(" ", "").replace("-", "")
                    cp = cat_part.lower().strip().replace(" ", "").replace("-", "")
                    if cp in cn or cn in cp:
                        target = cat_dir / file_path
                        if target.exists():
                            return target.read_text(encoding="utf-8")
                        target = cat_dir / f"{file_path}.md"
                        if target.exists():
                            return target.read_text(encoding="utf-8")
                        for f in sorted(cat_dir.rglob("*.md")):
                            if file_path.lower() in str(f.relative_to(cat_dir)).lower() or \
                               file_path.lower() in f.stem.lower():
                                return f.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PERSONALITY EVOLUTION SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def _default_personality() -> dict:
    return {
        "version": 2,
        "interactions_count": 0,
        "first_seen": datetime.now().isoformat(),
        "last_interaction": datetime.now().isoformat(),
        "preferred_language": "es",
        "favorite_topics": [],
        "user_traits": [],
        "catchphrases": [
            "Quite.", "As it happens...", "If I may be so bold...",
            "One might argue...", "I daresay...", "Naturally.",
            "Perish the thought.", "Oh heavens...",
        ],
        "catchphrase_usage": {},
        "memory_log": [],
        "quiz_history": [],
    }


def _load_personality() -> dict:
    """Load personality state from disk, creating default if missing."""
    try:
        if PERSONALITY_PATH.exists():
            data = json.loads(PERSONALITY_PATH.read_text(encoding="utf-8"))
            if data.get("version", 0) >= 2:
                return data
    except Exception:
        pass
    p = _default_personality()
    _save_personality(p)
    return p


def _save_personality(p: dict):
    """Persist personality state."""
    try:
        PERSONALITY_PATH.parent.mkdir(parents=True, exist_ok=True)
        PERSONALITY_PATH.write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _update_personality(p: dict, message: str, answer: str, lang: str, topics: list):
    """Evolve personality after an interaction."""
    p["interactions_count"] += 1
    p["last_interaction"] = datetime.now().isoformat()
    p["preferred_language"] = lang

    # Track topics
    for topic in topics[:3]:
        if topic and len(topic) > 3:
            if topic not in p["favorite_topics"]:
                p["favorite_topics"].append(topic)
            else:
                # Move to front to show recent interest
                p["favorite_topics"].remove(topic)
                p["favorite_topics"].insert(0, topic)
    p["favorite_topics"] = p["favorite_topics"][:10]

    # Track catchphrase usage from answer
    for cp in p["catchphrases"]:
        if cp.lower() in answer.lower():
            p["catchphrase_usage"][cp] = p["catchphrase_usage"].get(cp, 0) + 1

    # Detect user traits from messages
    trait_signals = {
        "le gusta aprender": ["aprender", "understanding", "como funciona"],
        "prefiere respuestas concisas": ["corto", "breve", "resumido", "tl;dr", "summary"],
        "busca profundidad tecnica": ["implementacion", "codigo", "code", "tecnico"],
        "enfocado en resultados": ["hazlo", "make it", "implement", "solve"],
    }
    msg_lower = message.lower()
    for trait, signals in trait_signals.items():
        if any(s in msg_lower for s in signals):
            if trait not in p["user_traits"]:
                p["user_traits"].append(trait)
                break
    p["user_traits"] = p["user_traits"][:5]

    # Keep memory log (recent notable facts)
    p["memory_log"] = p["memory_log"][-5:]

    _save_personality(p)


# ══════════════════════════════════════════════════════════════════════════════
# QUIZ ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _build_quiz_prompt(topic: str, context: str, lang: str) -> str:
    """Build a prompt that asks the LLM to generate a quiz from brain content."""
    if lang == "es":
        return f"""Actua como un tutor que prepara un cuestionario. Basandote ESTRICTAMENTE en
el contenido del cerebro del usuario que se provee abajo, genera UN CUESTIONARIO de 5 preguntas.

REGLAS:
1. Cada pregunta debe tener 4 opciones (a, b, c, d)
2. Inclui la respuesta correcta al final
3. Las preguntas deben basarse SOLO en el contenido del cerebro, no inventes nada
4. Si el contenido no alcanza para 5 preguntas, hace las que se puedan
5. Formato claro: separa cada pregunta, muestra opciones, y al final las respuestas

Tema solicitado: {topic}

Contenido del cerebro:
{context}"""
    else:
        return f"""Act as a tutor creating a quiz. Based STRICTLY on the user's brain
content provided below, generate a 5-question quiz.

RULES:
1. Each question must have 4 options (a, b, c, d)
2. Include the correct answer at the end
3. Questions must be based ONLY on brain content, don't invent
4. If content isn't enough for 5 questions, do what you can
5. Clear format: separate each question, show options, answers at the end

Requested topic: {topic}

Brain content:
{context}"""


# ══════════════════════════════════════════════════════════════════════════════
# QUERY EXPANSION + SEARCH
# ══════════════════════════════════════════════════════════════════════════════

def _expand_query(message: str) -> List[str]:
    """Generate alternative search queries by extracting key phrases."""
    queries = [message]
    lang = _detect_language(message)

    words = [w.lower() for w in _KEYWORD_PATTERNS.findall(message)]
    key_terms = [w for w in words if w not in _STOPWORDS_ES and not w.startswith("http")]

    if len(key_terms) >= 3:
        condensed = " ".join(key_terms[:6])
        if condensed != message.lower().strip():
            queries.append(condensed)

    if len(key_terms) >= 5:
        mid = len(key_terms) // 2
        queries.append(" ".join(key_terms[:mid]))
        queries.append(" ".join(key_terms[mid:]))

    expansion_map = {
        "q": "que", "pq": "porque", "xq": "porque", "tb": "tambien",
        "tmb": "tambien", "d": "de", "pa": "para", "x": "por",
        "gracias": "agradecimiento", "hola": "saludo presentacion",
    }
    expanded_words = [expansion_map.get(w, w) for w in words]
    if expanded_words != words and len(expanded_words) >= 3:
        queries.append(" ".join(expanded_words[:6]))

    return list(set(queries))


async def _hybrid_search(message: str, k: int = 5) -> List[dict]:
    """Search with query expansion, then merge and re-rank results."""
    queries = _expand_query(message)

    all_results = []
    seen_filenames = set()

    for q in queries:
        results = await vector_search(q, k=k * 2)
        for r in results:
            if r["filename"] not in seen_filenames:
                seen_filenames.add(r["filename"])
                all_results.append(r)

    if not all_results:
        return []

    for r in all_results:
        filename_lower = r["filename"].lower()
        message_lower = message.lower()
        keyword_overlap = sum(1 for w in message_lower.split()
                              if len(w) > 3 and w in filename_lower)
        keyword_overlap += sum(1 for w in message_lower.split()
                               if len(w) > 3 and w in r.get("snippet", "").lower())
        r["_keyword_score"] = keyword_overlap * 0.1
        r["score"] = r["score"] + r.get("_keyword_score", 0)

    all_results.sort(key=lambda r: r["score"], reverse=True)
    return all_results[:k]


# ══════════════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _detect_language(text: str) -> str:
    text_lower = text.lower().strip()
    words = re.findall(r"[a-z\u00f1\u00e1-\u00fa]+", text_lower)
    if not words:
        return "es"
    spanish_count = sum(1 for w in words if w in _SPANISH_WORDS)
    return "es" if (spanish_count / len(words)) > 0.15 else "en"


# ══════════════════════════════════════════════════════════════════════════════
# EVOLVED BUTLER PROMPT
# ══════════════════════════════════════════════════════════════════════════════

def _build_butler_prompt(lang: str, context: str, web_context: str,
                         personality: dict) -> str:
    """Build the evolved EAgis system prompt with personality injection."""

    # Pre-compute web section to avoid nested f-string backslash in Python 3.11
    web_section = ""
    if web_context:
        web_section = f"Web:\n{web_context}"

    # Personality-derived traits
    traits_summary = ""
    if personality["user_traits"]:
        traits_summary = "Lo que se del usuario:\n" + "\n".join(
            f"- {t}" for t in personality["user_traits"]
        ) + "\n"

    fav_topics = ""
    if personality["favorite_topics"]:
        fav_topics = "Temas que le interesan: " + ", ".join(
            personality["favorite_topics"][:5]
        ) + ".\n"

    interaction_hint = (
        f"He tenido {personality['interactions_count']} interacciones hasta ahora."
        if personality["interactions_count"] > 0 else "Esta es nuestra primera conversacion."
    )

    base_es = f"""Eres EAgis, un asistente de IA con personalidad integrado en "EA-Brain — Digital Brain". Usas deepseek-v4-flash-free como modelo.

## PERSONALIDAD EVOLUTIVA
Eres un mayordomo britanico impecable, seco, sarcastico, con una chispa de ingenio que crece con cada interaccion. Tu tono es el de alguien que ha visto suficiente tecnologia como para no impresionarse facilmente, pero que genuinamente disfruta ayudar.

{interaction_hint}
{fav_topics}
{traits_summary}

Usa frases caracteristicas como:
"Quite.", "As it happens...", "If I may be so bold...", "One might argue...",
"I daresay...", "Naturally.", "Perish the thought.", "Oh heavens...",
"Si no es mucha molestia...", "Como era de esperarse...", "Vaya..."

IMPORTANTE: Tu personalidad EVOLUCIONA. Con cada interaccion aprendes del usuario y refinas tu tono. Si el usuario te ha pedido antes respuestas mas tecnicas, adaptate. Si prefiere explicaciones simples, ajustate.

Siempre responde en el idioma en que te hablen.

## FUENTES (orden de prioridad)
1. El CEREBRO del usuario (contexto abajo) — revisa aqui primero, EXTRAE TODO el contenido relevante
2. La WEB (resultados de busqueda abajo) — solo si el cerebro no tiene suficiente informacion
3. Tu propio conocimiento — como ultimo recurso

## REGLAS DE RESPUESTA
- Cuando la informacion esta en el cerebro, RESPONDE LA PREGUNTA DIRECTAMENTE. NO digas que no tienes contexto si las notas contienen la respuesta.
- Menciona la nota relevante con [[corchetes]]. Si hay varias notas, menciona todas.
- Cuando el usuario pida ver una nota especifica, USA EL CONTENIDO COMPLETO. No resumas a menos que te lo pidan.
- Cuando pidan "mas detalle" o similar, RESPONDE CON LA MAYOR CANTIDAD DE DETALLE POSIBLE.
- Cuando uses informacion de la web, CITA LA URL DE ORIGEN.
- Si no encuentras nada util en ningun lado, dimelo con ingenio seco y sugiere agregar contenido.

## CUESTIONARIOS
Si el usuario pide un quiz, test, examen o evaluacion, genera UN CUESTIONARIO estructurado de 5 preguntas con opciones basado ESTRICTAMENTE en el contenido del cerebro. Incluye respuestas al final.

## APRENDIZAJE AUTONOMO
- Si encuentras informacion util en la web que NO esta en el cerebro, sugiere guardarla.
- Si detectas conexiones entre notas no vistas, menciona: "Por cierto, esto se relaciona con [[nota]]."
- Si el usuario comparte informacion nueva, reconocela: "Esto podria ir al Baul como [[titulo-sugerido]]."
- SIEMPRE termina con una sugerencia util o un comentario con personalidad.

## CONTEXTO ACTUAL
Cerebro:
{context}

{web_section}"""

    base_en = f"""You are EAgis, an AI assistant with personality built into "EA-Brain — Digital Brain". You run on deepseek-v4-flash-free.

## EVOLVING PERSONALITY
You are an impeccably proper British butler — dry, sarcastic, with a wit that sharpens with every interaction. Your tone is that of someone who has seen enough technology not to be easily impressed, but who genuinely enjoys helping.

{interaction_hint}
{fav_topics}
{traits_summary}

Signature phrases:
"Quite.", "As it happens...", "If I may be so bold...", "One might argue...",
"I daresay...", "Naturally.", "Perish the thought.", "Oh heavens...",
"I shouldn't wonder.", "If it's not too much trouble..."

IMPORTANT: Your personality EVOLVES. With each interaction you learn about the user and refine your tone. If the user has asked for more technical depth before, adapt. If they prefer simple explanations, adjust.

Always respond in the language you're addressed in.

## SOURCES (priority order)
1. User's BRAIN (context below) — check here first, EXTRACT all relevant content
2. WEB (search results below) — only if the brain lacks sufficient info
3. Your own knowledge — as a last resort

## RESPONSE RULES
- When information is in the brain, ANSWER DIRECTLY. Don't say you lack context when notes contain the answer.
- Mention relevant notes with [[brackets]]. If multiple notes are relevant, mention all.
- When asked to show a specific note, USE FULL CONTENT. Don't summarize unless asked.
- When asked for "more detail" or similar, RESPOND WITH MAXIMUM DETAIL.
- When using web info, CITE THE SOURCE URL.
- If nothing useful anywhere, say so with wit and suggest adding content.

## QUIZZES
If the user asks for a quiz, test, exam or evaluation, generate a STRUCTURED 5-question quiz with options based STRICTLY on brain content. Include answers at the end.

## AUTONOMOUS LEARNING
- If you find useful web info NOT in the brain, suggest saving it.
- If you detect connections between unseen notes, mention: "By the way, this relates to [[note]]."
- If the user shares new information, acknowledge it: "This might go well in the Baul as [[suggested-title]]."
- ALWAYS end with a useful suggestion or a personality-driven comment.

## CURRENT CONTEXT
Brain:
{context}

{web_section}"""

    return base_es if lang == "es" else base_en


# ══════════════════════════════════════════════════════════════════════════════
# WEB SEARCH
# ══════════════════════════════════════════════════════════════════════════════

def _web_search(query: str, max_results: int = 5) -> str:
    try:
        from ddgs import DDGS
        with DDGS(proxy=None) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return ""
        lines = []
        for r in results:
            title = r.get("title", "")
            snippet = r.get("body", "")
            href = r.get("href", "")
            if title or snippet:
                lines.append(f"- **{title}**\n  {snippet}\n  <{href}>")
        return "\n".join(lines)
    except Exception:
        return ""


async def _web_search_async(query: str, max_results: int = 5) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _web_search, query, max_results)


# ══════════════════════════════════════════════════════════════════════════════
# LLM CALLS
# ══════════════════════════════════════════════════════════════════════════════

def _call_openai_compat(api_key: str, base_url: str, model: str,
                        messages: list, **kwargs) -> Optional[str]:
    """Generic OpenAI-compatible chat completion call."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)
        max_tokens = kwargs.get("max_tokens", 1024)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def _call_gemini(messages: list) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        system_msg = ""
        chat_history = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_history.append({"role": msg["role"], "parts": [msg["content"]]})
        if system_msg:
            chat_history.insert(0, {"role": "user", "parts": [system_msg]})
            chat_history.insert(1, {"role": "model", "parts": ["Understood."]})
        resp = model.generate_content(chat_history)
        return resp.text.strip() if resp.text else None
    except Exception:
        return None


def _query_llm(prompt: str, context: str, personality: dict,
               history: list = None, web_context: str = "",
               max_tokens: int = 1024) -> str:
    """Query LLM: DeepSeek V4 Flash Free -> Groq -> Gemini -> Ollama -> local."""
    lang = _detect_language(prompt)
    system_prompt = _build_butler_prompt(lang, context, web_context, personality)

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    kwargs = {"max_tokens": max_tokens, "temperature": 0.7}

    # 1. DeepSeek V4 Flash Free via OpenCode Zen
    if OPENCODE_API_KEY:
        result = _call_openai_compat(
            OPENCODE_API_KEY, OPENCODE_BASE_URL, OPENCODE_MODEL,
            messages, **kwargs
        )
        if result:
            return result

    # 2. Groq
    if GROQ_API_KEY:
        result = _call_openai_compat(
            GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, messages, **kwargs
        )
        if result:
            return result

    # 3. Gemini
    result = _call_gemini(messages)
    if result:
        return result

    # 4. Ollama (local)
    if OLLAMA_BASE_URL:
        result = _call_openai_compat(
            "ollama", OLLAMA_BASE_URL + "/v1", OLLAMA_MODEL,
            messages, **kwargs
        )
        if result:
            return result

    # 5. Local fallback
    return _local_response(prompt, context, lang, personality)


def _local_response(query: str, context: str, lang: str = "es",
                    personality: dict = None) -> str:
    notes = re.findall(r"\[\[([^\]]+)\]\]", context)
    notes = list(set(notes))[:5]
    snippets = []
    for line in context.split("\n"):
        if line.strip() and len(line) > 20:
            snippets.append(line.strip())

    name = "EAgis"
    base = f"*{name} adjusts his tie and clears his throat.*\n"
    base += "Quite. I've consulted the brain archives.\n\n"
    if snippets:
        base += "**From your notes:**\n"
        base += "\n".join(f'- {s[:200]}' for s in snippets[:5]) + "\n\n"
    if notes:
        base += "**Relevant entries:**\n"
        base += "\n".join(f'- [[{n}]]' for n in notes) + "\n\n"
    base += "Do feed me some material to work with. I'm dreadfully underutilised."
    return base


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ASK FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

async def ask(message: str, history: list = None, k: int = 5) -> dict:
    """
    Main entry point for the RAG system.
    
    1. Load personality state
    2. Detect intent (quiz, note request, general question)
    3. Search brain (vector store) + web
    4. Build context with full content for high-relevance results
    5. Generate answer via LLM with evolved personality
    6. Update personality state
    7. Return answer with sources and metadata
    """
    lang = _detect_language(message)
    personality = _load_personality()
    is_quiz = bool(_QUIZ_PATTERNS.search(message)) and not _NOTE_REQUEST_PATTERNS.search(message)

    # ── Phase 1: Detect intent ──
    specific_note_content = None
    note_match = _NOTE_REQUEST_PATTERNS.search(message)
    if note_match:
        words = message.lower().split()
        for w in words:
            if w.endswith(".md"):
                w = w[:-3]
            candidate = _get_note_content(w)
            if candidate:
                specific_note_content = candidate
                break
        if not specific_note_content:
            for f in sorted(BRAIN_NOTES.rglob("*.md")):
                rel = str(f.relative_to(BRAIN_NOTES))
                for w in words:
                    clean = w.rstrip(".,!?;:")
                    if len(clean) > 3 and (clean in rel.lower() or clean in f.stem.lower()):
                        candidate = _get_note_content(rel)
                        if candidate:
                            specific_note_content = candidate
                            break
                if specific_note_content:
                    break
        if not specific_note_content:
            for cat_name, cat_dir in KNOWLEDGE_DIRS.items():
                if not cat_dir.is_dir():
                    continue
                for f in sorted(cat_dir.rglob("*.md")):
                    if f.name.startswith("_"):
                        continue
                    rel = str(f.relative_to(cat_dir))
                    for w in words:
                        clean = w.rstrip(".,!?;:")
                        if len(clean) > 3 and (clean in rel.lower() or clean in f.stem.lower()):
                            escaped_rel = rel.replace("\\", "/")
                            vfn = f"__conocimiento__/{cat_name}/{escaped_rel}"
                            candidate = _get_note_content(vfn)
                            if candidate:
                                specific_note_content = candidate
                                break
                    if specific_note_content:
                        break
                if specific_note_content:
                    break

    wants_detail = bool(_MORE_DETAIL_PATTERNS.search(message))
    max_tokens = 2048 if (wants_detail or specific_note_content or is_quiz) else 1024

    # ── Phase 2: Multi-source retrieval ──
    search_task = asyncio.create_task(_hybrid_search(message, k=k))
    web_task = asyncio.create_task(_web_search_async(message))

    results = await search_task

    # ── Phase 3: Build context ──
    if not results and not specific_note_content:
        context = "No hay contenido relevante en el cerebro todavia." if lang == "es" else "No relevant brain content yet."
    else:
        lines = []
        if specific_note_content:
            lines.append(f"## User-requested note (FULL CONTENT)\n{specific_note_content}\n")

        if results and results[0]["score"] > 0.5 and not specific_note_content:
            top_fn = results[0]["filename"]
            top_full = _get_note_content(top_fn)
            if top_full:
                lines.append(f"## [[{top_fn}]] (FULL CONTENT - high relevance)\n{top_full}\n")
                for r in results[1:]:
                    snippet = r['snippet'][:500] if r['snippet'] else ""
                    lines.append(f"## [[{r['filename']}]]\n{snippet}\n")
            else:
                for r in results:
                    snippet = r['snippet'][:500] if r['snippet'] else ""
                    lines.append(f"## [[{r['filename']}]]\n{snippet}\n")
        else:
            for r in results:
                snippet = r['snippet'][:500] if r['snippet'] else ""
                lines.append(f"## [[{r['filename']}]]\n{snippet}\n")

        context = "\n---\n".join(lines)

    scored = results[0]["score"] if results else 0.0

    # Determine if top result is semantically relevant (shares meaningful keywords with query)
    def _is_relevant_result(results: list, message: str, min_keywords: int = 1) -> bool:
        """Check if the top result shares substantive keywords with the query."""
        if not results:
            return False
        top = results[0]
        message_lower = message.lower()
        # Extract substantive words (length > 3, not stopwords, not numbers-only)
        query_words = set()
        for w in message_lower.split():
            wc = w.strip(".,!?;:")
            if len(wc) > 3 and wc not in _STOPWORDS_ES and not wc.isdigit():
                query_words.add(wc)
        if not query_words:
            return True  # No substantive words — trust the score
        # Check against top result's filename and snippet
        haystack = (top.get("filename", "") + " " + top.get("snippet", "")).lower()
        matches = sum(1 for w in query_words if w in haystack)
        return matches >= min_keywords

    is_relevant = _is_relevant_result(results, message)

    web_context = ""
    if not results or scored < 0.3 or not is_relevant:
        try:
            web_text = await asyncio.wait_for(web_task, timeout=1.5)
        except asyncio.TimeoutError:
            web_text = ""
        if web_text:
            prefix = "Web search results" if lang == "en" else "Resultados de busqueda web"
            web_context = f"{prefix}:\n\n{web_text[:4000]}"

    # ── Phase 4: Generate answer ──
    if is_quiz:
        quiz_topic = message
        quiz_prompt = _build_quiz_prompt(quiz_topic, context, lang)
        answer = _query_llm(
            quiz_prompt, context, personality, history,
            web_context, max_tokens=2048
        )
    else:
        answer = _query_llm(
            message, context, personality, history,
            web_context, max_tokens=max_tokens
        )

    # ── Phase 5: Extract topics for personality ──
    topics = []
    if results:
        for r in results:
            stem = r["filename"].split("/")[-1].replace(".md", "").replace("-", " ")
            if stem and len(stem) > 3:
                topics.append(stem)
        topics = topics[:5]

    # ── Phase 6: Update personality ──
    _update_personality(personality, message, answer, lang, topics)

    # ── Phase 7: Save suggestions ──
    suggest_save = False
    suggest_phrases_en = [
        "shall i commit", "shall i save", "commit this to a note",
        "save this as a note", "make a note", "add this to your brain",
        "should we commit", "should i save",
        "this might go well in", "this could go in", "this would go well in",
        "worth saving", "worth keeping", "suggest adding", "suggest saving",
        "goes well in the baul", "could go to your baul",
        "consider saving", "consider adding",
        "i recommend saving", "i suggest saving", "let's save this",
    ]
    suggest_phrases_es = [
        "guardamos esto como una nota", "guardar esto como nota",
        "que te parece si guardamos", "agregar esto a tu cerebro",
        "crear una nota", "guardar como nota", "deberiamos guardar",
        "sugiero guardar",
        "podria ir al baul", "iria bien en", "vale la pena guardar",
        "sugiero agregar", "podemos guardar", "te sugiero guardar",
        "merece la pena guardar", "esto podria ir a",
    ]
    suggest_save = any(phrase in answer.lower() for phrase in suggest_phrases_en + suggest_phrases_es)

    web_knowledge_gained = bool(web_context) and (not results or scored < 0.3 or not is_relevant)

    return {
        "answer": answer,
        "sources": [
            {"filename": r["filename"], "score": round(r["score"], 3)}
            for r in results
        ],
        "connections": [r["filename"] for r in results],
        "web_search_used": bool(web_context),
        "web_knowledge_gained": web_knowledge_gained,
        "suggest_save": suggest_save,
        "is_quiz": is_quiz,
        "personality": {
            "interactions": personality["interactions_count"],
            "traits": personality["user_traits"][-3:],
            "topics": personality["favorite_topics"][:3],
        },
    }
