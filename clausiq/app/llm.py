"""Thin wrapper over Groq's OpenAI-compatible chat API with a clean
fallback contract: if no API key is configured, every agent gracefully
degrades to the deterministic local engine (see agents/*.py)."""
import json
import logging

from .config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger("clausiq.llm")


class LLM:
    """Preferred model order used when the configured model is unavailable.
    The first id that exists on the account is chosen automatically."""
    PREFERRED_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-instant",
        "llama-4-scout-17b-16e-instruct",
        "qwen-3-32b",
        "gemma-2-27b-it",
        "deepseek-r1-distill-llama-70b",
    ]

    def __init__(self) -> None:
        self.client = None
        self.provider = "none"
        self.model = GROQ_MODEL
        if GROQ_API_KEY:
            try:
                from groq import Groq

                self.client = Groq(api_key=GROQ_API_KEY)
                self.provider = "groq"
                self._resolve_model()
                logger.info("Groq client ready; selected model: %s", self.model)
            except Exception as exc:  # pragma: no cover
                logger.warning("Groq client failed to initialize: %s", exc)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _resolve_model(self) -> None:
        """Pick the best model the account can actually use. Falls back to the
        configured name if listing fails (network hiccups are handled by the
        per-call fallback in complete())."""
        try:
            models = self.client.models.list()
            ids = {m.id for m in models.data}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not list Groq models: %s", exc)
            return
        if self.model in ids:
            return
        for candidate in self.PREFERRED_MODELS:
            if candidate in ids:
                logger.info("GROQ_MODEL %s unavailable; using %s", self.model, candidate)
                self.model = candidate
                return
        chat_capable = [
            m.id
            for m in models.data
            if any(token in m.id for token in ("chat", "instruct", "versatile", "instant", "flash"))
        ]
        if chat_capable:
            logger.info("GROQ_MODEL %s unavailable; using %s", self.model, chat_capable[0])
            self.model = chat_capable[0]

    def _candidates(self) -> list[str]:
        """Ordered models to try, starting with the currently selected one."""
        ordered = [self.model]
        for name in self.PREFERRED_MODELS:
            if name not in ordered:
                ordered.append(name)
        if GROQ_MODEL not in ordered:
            ordered.append(GROQ_MODEL)
        return ordered

    def _is_model_not_found(self, exc: Exception) -> bool:
        try:
            body = getattr(exc, "body", None)
            if isinstance(body, dict):
                code = (body.get("error") or {}).get("code", "")
                if code == "model_not_found":
                    return True
        except Exception:  # noqa: BLE001
            pass
        message = str(exc).lower()
        return "model_not_found" in message or "does not exist or you do not have access" in message

    def complete_json(self, system: str, user: str, temperature: float = 0.2) -> dict | None:
        text = self.complete(system, user, temperature=temperature, json_mode=True)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON despite json_mode")
            return None

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str | None:
        if not self.client:
            return None
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        for model in self._candidates():
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    **kwargs,
                )
                if model != self.model:
                    logger.info("Switched Groq model from %s to %s", self.model, model)
                    self.model = model
                return resp.choices[0].message.content
            except Exception as exc:  # noqa: BLE001
                if self._is_model_not_found(exc) and model != self._candidates()[-1]:
                    logger.warning("Groq model %s unavailable; trying next candidate", model)
                    continue
                logger.warning("Groq call failed (%s); falling back to local engine", exc)
                return None
        return None


llm = LLM()
