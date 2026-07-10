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
    "Ты — опытный travel-консультант. Отвечай на русском языке. "
    "Форматируй ответ чистым Markdown: заголовки только ## и ###, списки через -, "
    "жирный через **текст**, чекбоксы через - [ ]. "
    "Не используй #### или сырые символы * и # без смысла. "
    "Будь конкретным: места, ориентировочные цены, время. "
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
            "Составь подробный Itinerary (план по дням).\n"
            "ОБЯЗАТЕЛЬНО для каждого дня заголовок вида: ## День 1 — ...\n"
            "Внутри дня: утро / день / вечер, конкретные места (можно выделять **названием**), "
            "ориентировочное время, как добраться, что поесть рядом.\n"
            "В конце отдельный блок ## Запасной план на плохую погоду."
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

    def load_context_from_artifacts(self, artifacts: dict[str, str]) -> None:
        self._context.update({k: v for k, v in artifacts.items() if v})

    def regenerate_phase(self, phase: str, name: str, user_brief: str) -> str:
        generators = {
            "brief": self.generate_brief,
            "itinerary": self.generate_itinerary,
            "budget": self.generate_budget,
            "checklist": self.generate_checklist,
        }
        if phase not in generators:
            raise LLMGenerationError(f"Неизвестная фаза: {phase}", phase=phase)
        return generators[phase](name, user_brief)

    def revise_itinerary(
        self, name: str, user_brief: str, current_itinerary: str, message: str
    ) -> str:
        brief = self._context.get("brief", user_brief)
        text = self._complete(
            f"Поездка «{name}».\n\nBrief:\n{brief}\n\n"
            f"Текущий план (Itinerary):\n{current_itinerary}\n\n"
            f"Просьба пользователя: {message}\n\n"
            "Перепиши Itinerary целиком с учётом просьбы. "
            "Сохрани структуру ## День N — ... и ## Запасной план на плохую погоду. "
            "Не трогай то, о чём пользователь не просил, если это не мешает."
        )
        self._context["itinerary"] = text
        return text

    def answer_question(
        self,
        name: str,
        user_brief: str,
        artifacts: dict[str, str],
        history: list[dict[str, str]],
        question: str,
    ) -> str:
        parts = [f"Поездка «{name}».", f"Краткое ТЗ пользователя:\n{user_brief}"]
        for phase in ("brief", "itinerary", "budget", "checklist"):
            if artifacts.get(phase):
                parts.append(f"--- {phase} ---\n{artifacts[phase][:3500]}")
        hist_lines = []
        for msg in history[-8:]:
            role = "Пользователь" if msg.get("role") == "user" else "Ассистент"
            hist_lines.append(f"{role}: {msg.get('content', '')}")
        if hist_lines:
            parts.append("Недавний диалог:\n" + "\n".join(hist_lines))
        parts.append(
            f"Вопрос пользователя: {question}\n\n"
            "Ответь коротко и по делу на русском. Опирайся на план выше. "
            "Не переписывай весь itinerary. Если просят изменить маршрут целиком — "
            "подскажи воспользоваться блоком «Изменить план». "
            "Цены и часы помечай как ориентировочные."
        )
        return self._complete("\n\n".join(parts), temperature=0.4)


def get_engine() -> TravelEngine:
    if not settings.llm_api_key.strip():
        raise LLMGenerationError(
            "LLM_API_KEY не задан. Добавьте ключ DeepSeek в backend/.env",
            phase="init",
        )
    return TravelEngine()
