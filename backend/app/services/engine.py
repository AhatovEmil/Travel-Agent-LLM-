"""Travel LLM engine — DeepSeek only, no template fallback."""

from __future__ import annotations

import logging
import time

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    def __init__(self, message: str, phase: str = ""):
        self.phase = phase
        super().__init__(message)


SYSTEM_PROMPT = (
    "Ты — опытный travel-консультант. Отвечай на русском языке, структурированным "
    "Markdown. Будь конкретным: места, ориентировочные цены, время. "
    "Помечай, что цены и часы работы — ориентировочные и их нужно проверять."
)


class TravelEngine:
    name = "travel-llm"

    def __init__(self) -> None:
        self._context: dict[str, str] = {}

    def _models_to_try(self) -> list[str]:
        models = [settings.llm_model]
        for model in settings.llm_model_fallbacks.split(","):
            model = model.strip()
            if model and model not in models:
                models.append(model)
        return models

    def _friendly_http_error(self, status: int, detail: str) -> str:
        if status == 429:
            return "Лимит запросов (HTTP 429). Подождите минуту и повторите."
        if status == 401:
            return "Неверный LLM_API_KEY. Проверьте ключ DeepSeek в backend/.env"
        if status == 402:
            return "Недостаточно баланса DeepSeek. Пополните счёт на platform.deepseek.com"
        return f"HTTP {status}: {detail}"

    def _complete(self, prompt: str, temperature: float = 0.5) -> str:
        errors: list[str] = []
        for model in self._models_to_try():
            for attempt in range(4):
                try:
                    response = httpx.post(
                        f"{settings.llm_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.llm_api_key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": settings.app_name,
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": temperature,
                        },
                        timeout=120,
                    )
                    if response.status_code == 429:
                        wait = min(2**attempt, 16)
                        logger.warning("LLM 429 model=%s sleep=%ss", model, wait)
                        errors.append(f"429 ({model})")
                        time.sleep(wait)
                        continue
                    if response.status_code >= 400:
                        detail = response.text[:300]
                        logger.warning("LLM HTTP %s: %s", response.status_code, detail)
                        errors.append(self._friendly_http_error(response.status_code, detail))
                        break
                    content = response.json()["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
                    errors.append("пустой ответ")
                except Exception as exc:
                    logger.warning("LLM request failed: %s", exc)
                    errors.append(str(exc))
                    break
        raise LLMGenerationError("; ".join(errors[-3:]) if errors else "неизвестная ошибка LLM")

    def generate_brief(self, name: str, user_brief: str) -> str:
        text = self._complete(
            f"Поездка «{name}».\n\nОписание от пользователя:\n{user_brief}\n\n"
            "Составь документ Brief:\n"
            "## Куда и когда\n## Цель поездки\n## Участники / формат\n"
            "## Бюджет (если указан)\n## Интересы и ограничения\n"
            "## Что нужно уточнить\n"
            "Если чего-то не хватает — сделай разумные допущения и явно их перечисли."
        )
        self._context["brief"] = text
        return text

    def generate_itinerary(self, name: str, user_brief: str) -> str:
        brief = self._context.get("brief", user_brief)
        text = self._complete(
            f"Поездка «{name}».\n\nBrief:\n{brief}\n\n"
            "Составь подробный Itinerary (план по дням):\n"
            "Для каждого дня: утро / день / вечер, места, ориентировочное время, "
            "как добраться, что поесть рядом. В конце — запасной план на плохую погоду."
        )
        self._context["itinerary"] = text
        return text

    def generate_budget(self, name: str, user_brief: str) -> str:
        brief = self._context.get("brief", user_brief)
        itinerary = self._context.get("itinerary", "")
        text = self._complete(
            f"Поездка «{name}».\n\nBrief:\n{brief}\n\nItinerary (фрагмент):\n{itinerary[:2500]}\n\n"
            "Составь Budget:\n"
            "## Итого (ориентир)\n## Жильё\n## Транспорт\n## Еда\n## Активности / билеты\n"
            "## Непредвиденное (10–15%)\n"
            "Дай суммы в рублях (или в валюте, если пользователь указал другую). "
            "Пометь, что цены ориентировочные."
        )
        self._context["budget"] = text
        return text

    def generate_checklist(self, name: str, user_brief: str) -> str:
        brief = self._context.get("brief", user_brief)
        text = self._complete(
            f"Поездка «{name}».\n\nBrief:\n{brief}\n\n"
            "Составь Checklist подготовки:\n"
            "## Документы\n## Билеты и жильё\n## Вещи\n## Деньги и связь\n"
            "## За 1 день до выезда\n## В день выезда\n"
            "Сделай списки с чекбоксами Markdown `- [ ]`."
        )
        self._context["checklist"] = text
        return text


def get_engine() -> TravelEngine:
    if not settings.llm_api_key.strip():
        raise LLMGenerationError(
            "LLM_API_KEY не задан. Добавьте ключ DeepSeek в backend/.env",
            phase="init",
        )
    return TravelEngine()
