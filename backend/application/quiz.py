"""Quiz generation use case — batch generation with chunking."""
import re
from backend.ports.llm import LLMRouter
from backend.ports.search import VectorSearchPort
from backend.infrastructure.logger import get_logger

logger = get_logger("application.quiz")

CHUNK_SIZE = 25


class QuizService:
    """Generates quizzes in chunks, combining into one document."""

    def __init__(self, llm_router: LLMRouter, vector_search: VectorSearchPort):
        self._llm = llm_router
        self._vector = vector_search

    async def generate(self, topic: str, count: int, lang: str = "es") -> str:
        """Generate a large quiz in chunks of CHUNK_SIZE."""
        # Search brain for relevant content
        results = await self._vector.search(topic, k=5)
        context_lines = []
        for r in results:
            context_lines.append(f"## [[{r.filename}]]\n{r.snippet}\n")
        context = "\n---\n".join(context_lines) if context_lines else "No hay contenido relevante."

        parts = []
        for batch_start in range(0, count, CHUNK_SIZE):
            start = batch_start + 1
            end = min(batch_start + CHUNK_SIZE, count)
            batch_n = end - start + 1

            prompt = self._build_chunk_prompt(topic, start, end, batch_n, count, context)

            system = f"""Generate multiple-choice quiz questions about: {topic}

Requirements:
- EXACTLY {batch_n} questions, numbered {start} through {end}
- EVERY question MUST be about: {topic}. Do NOT generate questions about other subjects.
- Each question has exactly 4 options (A, B, C, D)
- Mark correct answer on its own line: "**Respuesta correcta:** B"
- Base ALL questions on the brain content below
- Output ONLY the questions — no intro, no outro

CONTENT:
{context[:4000]}"""

            messages = [{"role": "system", "content": system}]
            messages.append({"role": "user", "content": prompt})

            result = await self._llm.race(
                messages,
                max_tokens=min(1500 + batch_n * 40, 3000),
                timeout=45.0,
            )

            if result and len(result) > 30:
                parts.append(result)
            else:
                # Fallback prompt
                fallback = (
                    f"Write {batch_n} multiple-choice questions about {topic}. "
                    f"Number them {start}-{end}. Each has 4 options (A-D) and a correct answer. "
                    f"Content:\n{context[:3000]}"
                )
                messages[-1] = {"role": "user", "content": fallback}
                result2 = await self._llm.race(
                    messages, max_tokens=min(1500 + batch_n * 40, 3000), timeout=45.0
                )
                if result2 and len(result2) > 30:
                    parts.append(result2)

        if not parts:
            return (f"*No se pudo generar el cuestionario sobre '{topic}'*" if lang == "es"
                    else f"*Could not generate quiz about '{topic}'*")

        header = f"# Quiz: {topic.title()}\n\n**Total: {count} preguntas**\n\n---\n\n"
        return header + "\n\n".join(parts)

    def _build_chunk_prompt(self, topic: str, start: int, end: int,
                            batch_n: int, total: int, context: str) -> str:
        return (
            f"Generate questions {start}-{end} of {total} about: {topic}\n\n"
            f"EXACTLY {batch_n} questions. ALL about {topic}."
        )
