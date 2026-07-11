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
            "ОБЯЗАТЕЛЬНО для каждого дня заголовок:\n"
            "## День 1 — YYYY-MM-DD — краткий заголовок\n"
            "(даты подряд от «Дата начала» из brief; если даты нет — от сегодня).\n"
            "Внутри дня слоты строго в формате:\n"
            "### HH:MM–HH:MM — Название места\n"
            "Под слотом: что делать, как добраться, ориентир по еде рядом.\n"
            "В конце отдельный блок ## Запасной план на плохую погоду.\n\n"
            "ВАЖНО про места:\n"
            "- Указывай только реально существующие места, улицы, парки, музеи и заведения "
            "в этом направлении (или широко известные в регионе).\n"
            "- Не выдумывай несуществующие названия. Если точного места не знаешь — "
            "пиши тип и район («кафе в центре», «набережная», «краеведческий музей»), "
            "без фантазийных имён.\n"
            "- Весь текст плана на русском."
        )
        text = self.ensure_structured_itinerary(text)
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
            "Сохрани формат дней ## День N — дата — заголовок и слотов ### HH:MM–HH:MM — место. "
            "Только реальные места в направлении поездки, без выдуманных названий. "
            "Текст на русском. "
            "Сохрани структуру ## День N — YYYY-MM-DD — … и слоты "
            "### HH:MM–HH:MM — Место, плюс ## Запасной план на плохую погоду. "
            "Не трогай то, о чём пользователь не просил, если это не мешает."
        )
        text = self.ensure_structured_itinerary(text)
        self._context["itinerary"] = text
        return text

    def fix_unverified_places(
        self,
        itinerary: str,
        destination: str,
        bad_places: list[str],
    ) -> str:
        """Заменяет места, не найденные на карте, на реальные или мягкие формулировки."""
        if not bad_places:
            return itinerary
        listed = "\n".join(f"- {p}" for p in bad_places[:24])
        rewritten = self._complete(
            f"Направление поездки: {destination}.\n\n"
            "Эти названия мест НЕ найдены на карте OpenStreetMap и скорее всего ВЫДУМАНЫ:\n"
            f"{listed}\n\n"
            "Перепиши itinerary ЦЕЛИКОМ:\n"
            "- замени каждое выдуманное место на РЕАЛЬНОЕ известное место в этом направлении "
            "ИЛИ на мягкую формулировку без фантазийного имени "
            "(например: «кафе в центре», «набережная», «городской парк», «краеведческий музей»);\n"
            "- не оставляй выдуманные названия;\n"
            "- сохрани формат ## День N — YYYY-MM-DD — … и слоты ### HH:MM–HH:MM — Место;\n"
            "- в конце ## Запасной план на плохую погоду;\n"
            "- текст на русском.\n\n"
            f"Исходный план:\n{itinerary[:7000]}",
            temperature=0.35,
        )
        text = rewritten.strip() if rewritten else itinerary
        return self.ensure_structured_itinerary(text)

    def itinerary_needs_structure(self, text: str) -> bool:
        from .parse import parse_itinerary_days

        days = parse_itinerary_days(text)
        if not days:
            return True
        structured = 0
        for day in days:
            if day.get("slots"):
                structured += 1
        # если ни у одного дня нет слотов — нужен дожим
        return structured == 0

    def ensure_structured_itinerary(self, text: str) -> str:
        """Один авто-дожим, если LLM не выдал слоты ### HH:MM–HH:MM."""
        if not text or not self.itinerary_needs_structure(text):
            return text
        logger.info("Itinerary missing slots — requesting structured rewrite")
        rewritten = self._complete(
            "Перепиши план ниже в строгий формат.\n"
            "Для каждого дня: ## День N — YYYY-MM-DD — заголовок\n"
            "Внутри дня только слоты вида:\n"
            "### HH:MM–HH:MM — Название места\n"
            "Краткое описание под слотом.\n"
            "В конце: ## Запасной план на плохую погоду\n\n"
            f"Исходный план:\n{text[:6000]}"
        )
        return rewritten if rewritten.strip() else text

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

    def adjust_day(
        self,
        name: str,
        user_brief: str,
        day_markdown: str,
        reason: str,
        message: str = "",
    ) -> str:
        reason_text = {
            "late": "турист опаздывает, нужно сжать/сдвинуть оставшиеся слоты",
            "rain": "плохая погода / дождь — заменить outdoor на indoor",
            "custom": message or "нужна точечная правка дня",
        }.get(reason, message or reason)
        return self._complete(
            f"Поездка «{name}».\nBrief:\n{user_brief}\n\n"
            f"Текущий день:\n{day_markdown}\n\n"
            f"Ситуация: {reason_text}\n\n"
            "Перепиши ТОЛЬКО этот день целиком: сохрани заголовок ## День N — YYYY-MM-DD — … "
            "и слоты ### HH:MM–HH:MM — Место. Не пиши другие дни и не пиши запасной план. "
            "Только реальные места, текст на русском."
        )

    def rebuild_from_votes(
        self,
        name: str,
        user_brief: str,
        itinerary: str,
        vote_summary: str,
    ) -> str:
        text = self._complete(
            f"Поездка «{name}».\nBrief:\n{user_brief}\n\n"
            f"Текущий Itinerary:\n{itinerary}\n\n"
            f"Голоса спутников:\n{vote_summary}\n\n"
            "Перепиши Itinerary целиком с учётом голосов: "
            "слоты с преобладанием skip замени на альтернативы, "
            "want сохрани. Формат: ## День N — YYYY-MM-DD — … и "
            "### HH:MM–HH:MM — Место. В конце ## Запасной план на плохую погоду. "
            "Только реальные места в направлении, без выдуманных названий."
        )
        text = self.ensure_structured_itinerary(text)
        self._context["itinerary"] = text
        return text

    def enrich_survival_phrases(self, destination: str, region_label: str) -> list[dict]:
        from .street_smart import parse_json_list

        raw = self._complete(
            f"Направление: {destination} ({region_label}).\n"
            "Верни ТОЛЬКО JSON вида:\n"
            '{"phrases":[{"local":"...","latin":"...","ru":"..."}, ...]}\n'
            "Ровно 8 живых уличных фраз.\n"
            "Правила языка поля local:\n"
            "- Россия / русскоязычный город / СНГ: local на РУССКОМ (не английский!). "
            "latin — транслит кириллицы.\n"
            "- Грузия: local на грузинском; Турция — турецкий; Западная Европа — язык страны.\n"
            "- Иначе — язык страны направления, не подставляй английский «по умолчанию».\n"
            "ru — короткий смысл по-русски. Без markdown и пояснений.",
            temperature=0.45,
        )
        items = parse_json_list(raw, "phrases") or []
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                continue
            local = str(item.get("local") or "").strip()
            latin = str(item.get("latin") or "").strip()
            ru = str(item.get("ru") or "").strip()
            if local and ru:
                cleaned.append({"local": local, "latin": latin, "ru": ru})
        return cleaned[:8]

    def enrich_traps(self, destination: str, region_label: str) -> list[dict]:
        from .street_smart import parse_json_list

        raw = self._complete(
            f"Направление: {destination} ({region_label}).\n"
            "Верни ТОЛЬКО JSON:\n"
            '{"traps":[{"title":"...","how":"..."}, ...]}\n'
            "5–7 типичных туристических разводов/ловушек и как отшить коротко, дерзко, по делу. "
            "На русском. Без markdown.",
            temperature=0.55,
        )
        items = parse_json_list(raw, "traps") or []
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            how = str(item.get("how") or "").strip()
            if title and how:
                cleaned.append({"title": title, "how": how})
        return cleaned[:7]

    def generate_day_quest(
        self,
        destination: str,
        day_title: str,
        places: list[str],
    ) -> list[str]:
        from .street_smart import parse_json_list

        place_line = ", ".join(places[:6]) if places else "места дня из плана"
        raw = self._complete(
            f"Город: {destination}. День: {day_title}. Точки: {place_line}.\n"
            "Придумай ровно 3 микромиссии для туриста «не выглядеть туристом». "
            "Коротко, игриво, выполнимо за день. Верни ТОЛЬКО JSON:\n"
            '{"missions":["...","...","..."]}',
            temperature=0.7,
        )
        items = parse_json_list(raw, "missions") or []
        texts = [str(x).strip() for x in items if str(x).strip()]
        return texts[:3]


def get_engine() -> TravelEngine:
    if not settings.llm_api_key.strip():
        raise LLMGenerationError(
            "LLM_API_KEY не задан. Добавьте ключ DeepSeek в backend/.env",
            phase="init",
        )
    return TravelEngine()
