"""Google Gemini provider."""
from typing import Optional
from backend.ports.llm import LLMProvider
from backend.infrastructure.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini — free tier, uses google.generativeai."""

    def __init__(self):
        self._api_key = GEMINI_API_KEY or ""
        self._model_name = GEMINI_MODEL

    @property
    def name(self) -> str:
        return "gemini"

    async def generate(self, messages: list[dict], max_tokens: int = 1024,
                       temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        if not self._api_key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model_name)
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
        except Exception as e:
            logger.warning("[gemini] Generation failed: %s", e)
            return None
