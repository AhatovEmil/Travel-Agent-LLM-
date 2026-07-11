"""Street Smart — survival, traps, taste, arrival, day quests."""

from __future__ import annotations

import json
import re
from typing import Any

from .parse import extract_destination, parse_itinerary_days

Region = str  # ge | tr | eu | ru | default

_CYR = re.compile(r"[а-яё]", re.I)
_LAT = re.compile(r"[a-z]", re.I)

# Типичные русские/СНГ маркеры в названии города
_RU_HINTS = (
    "москв",
    "петербург",
    "питер",
    "сочи",
    "казан",
    "калининград",
    "екатеринбург",
    "новосибир",
    "ноябрьск",
    "тюмен",
    "краснояр",
    "владивосток",
    "хабаров",
    "иркутск",
    "самар",
    "нижний",
    "новгород",
    "ростов",
    "уфа",
    "перм",
    "воронеж",
    "волгоград",
    "краснодар",
    "якутск",
    "мурманск",
    "архангельск",
    "челябинск",
    "омск",
    "томск",
    "барнаул",
    "алтай",
    "карел",
    "байкал",
    "крым",
    "ялта",
    "севастопол",
    "симферопол",
    "минск",
    "росси",
    "russia",
)


def detect_region(destination: str) -> Region:
    d = (destination or "").lower().strip()
    if any(x in d for x in ("батуми", "тбилиси", "грузи", "batumi", "tbilisi", "georgia", "кутаиси")):
        return "ge"
    if any(x in d for x in ("стамбул", "анталь", "istanbul", "antalya", "турци", "turkey", "каппадок")):
        return "tr"
    if any(
        x in d
        for x in (
            "париж",
            "рим",
            "барселон",
            "берлин",
            "праг",
            "амстердам",
            "вен",
            "милан",
            "лондон",
            "paris",
            "rome",
            "berlin",
            "prague",
            "italy",
            "франц",
            "испан",
            "герман",
            "мадрид",
            "лиссабон",
            "вена",
            "vienna",
        )
    ):
        return "eu"
    if any(x in d for x in _RU_HINTS):
        return "ru"
    if re.search(r"(ск|цк|ов|ев|ин|град|поль|бург)$", d.replace(" ", "")):
        # Ноябрьск, Екатеринбург, Севастополь…
        cyr = len(_CYR.findall(d))
        if cyr >= 3:
            return "ru"
    # Кириллическое название без явного зарубежья → русскоязычный контекст
    cyr = len(_CYR.findall(d))
    lat = len(_LAT.findall(d))
    if cyr >= 3 and cyr >= lat:
        return "ru"
    return "default"


_PACKS: dict[Region, dict[str, Any]] = {
    "ge": {
        "label": "Грузия",
        "currency": "лари (GEL)",
        "emergency": [
            {"title": "Единый экстренный", "value": "112"},
            {"title": "Полиция", "value": "112"},
            {"title": "Скорая", "value": "112"},
        ],
        "tips": [
            "SIM: Magti / Geocell в аэропорту или киосках — паспорт под рукой.",
            "Такси: Bolt/Yandex надёжнее, чем схватывать у обочины.",
            "Чаевые: 5–10% в кафе приятны, но не обязательны как закон.",
            "Вода из-под крана в Батуми/Тбилиси обычно ок, но бутылка не помешает.",
        ],
        "taxi_line": "გთხოვთ, წაიყვანეთ აქ — gthkhovt, tsaiqvanet ak (пожалуйста, отвезите сюда)",
        "phrases": [
            {"local": "გამარჯობა", "latin": "gamarjoba", "ru": "Здравствуйте"},
            {"local": "მადლობა", "latin": "madloba", "ru": "Спасибо"},
            {"local": "რა ღირს?", "latin": "ra ghirs?", "ru": "Сколько стоит?"},
            {"local": "არა, მადლობა", "latin": "ara, madloba", "ru": "Нет, спасибо"},
            {"local": "სად არის…?", "latin": "sad aris…?", "ru": "Где находится…?"},
            {"local": "ინგლისურად?", "latin": "inglisurad?", "ru": "По-английски?"},
            {"local": "გემრიელია!", "latin": "gemrielia!", "ru": "Вкусно!"},
            {"local": "დახმარება!", "latin": "dakhmareba!", "ru": "Помогите!"},
        ],
        "traps": [
            {
                "title": "«Дружелюбный гид» у вокзала",
                "how": "Предлагает тур/такси «по себестоимости». Откажитесь: «არა, მადლობა» и идите к Bolt.",
            },
            {
                "title": "Меню без цен",
                "how": "Спросите цену до заказа. Если юлят — вставайте и уходите.",
            },
            {
                "title": "Обмен валюты «на улице»",
                "how": "Только банки/официальные обменники. Курс «для своих» = развод.",
            },
            {
                "title": "Таксист без счётчика",
                "how": "Фиксируйте цену в приложении. Наличные «как договоримся» часто ×2.",
            },
            {
                "title": "Чурчхела «элитная» у туристической арки",
                "how": "Берите на рынке, где покупают местные. Разница в цене — в 2–3 раза.",
            },
        ],
        "taste": [
            {"dish": "Хачапури по-аджарски", "where": "пекарня / семейное кафе в стороне от набережной"},
            {"dish": "Хинкали", "where": "место, где едят руками и не стесняются бульона"},
            {"dish": "Чурчхела", "where": "рынок, не витрина у фонтана"},
            {"dish": "Лимонад из тархуна", "where": "уличная точка или супермаркет"},
            {"dish": "Цыплёнок тапака", "where": "локальный ресторан без англо-меню на 4 языка"},
            {"dish": "Цинцкаро / саперави", "where": "винный бар с бочками, не «дегустация для круиза»"},
        ],
        "arrival": [
            "Деньги: банкомат в зале прилёта, снимите немного лари сразу.",
            "Связь: SIM-киоск или eSIM — интернет важнее красивого селфи.",
            "Вода/кофе: купите бутылку, присядьте 5 минут, не бегите в такси в панике.",
            "До жилья: Bolt/Yandex, адрес на латинице в буфере обмена.",
            "Первый якорь: короткая прогулка у жилья — аптека, магазин, ориентир «где я».",
        ],
    },
    "tr": {
        "label": "Турция",
        "currency": "лира (TRY)",
        "emergency": [
            {"title": "Экстренный", "value": "112"},
            {"title": "Полиция", "value": "155"},
            {"title": "Скорая", "value": "112"},
        ],
        "tips": [
            "SIM: Turkcell / Vodafone в аэропорту — паспорт.",
            "Такси: BiTaksi / Uber где есть; жёлтые у аэропорта часто завышают.",
            "Чаевые: округление в кафе, 5–10% в ресторане нормально.",
            "Торг на базаре — игра, на ценнике в сети — нет.",
        ],
        "taxi_line": "Lütfen buraya götürün (пожалуйста, отвезите сюда)",
        "phrases": [
            {"local": "Merhaba", "latin": "merhaba", "ru": "Здравствуйте"},
            {"local": "Teşekkürler", "latin": "teshekkurler", "ru": "Спасибо"},
            {"local": "Ne kadar?", "latin": "ne kadar?", "ru": "Сколько стоит?"},
            {"local": "Hayır, teşekkürler", "latin": "hayir, teshekkurler", "ru": "Нет, спасибо"},
            {"local": "Nerede…?", "latin": "nerede…?", "ru": "Где…?"},
            {"local": "İngilizce biliyor musunuz?", "latin": "ingilizce biliyor musunuz?", "ru": "Говорите по-английски?"},
            {"local": "Çok lezzetli!", "latin": "chok lezzetli!", "ru": "Очень вкусно!"},
            {"local": "Yardım!", "latin": "yardim!", "ru": "Помогите!"},
        ],
        "traps": [
            {
                "title": "«Бесплатная» экскурсия с чаем",
                "how": "Часто заканчивается ковром за $800. «Hayır, teşekkürler» и ноги в руки.",
            },
            {
                "title": "Подошва «чистильщика»",
                "how": "Классика Стамбула: испачкали — требуют деньги. Идите мимо, не останавливайтесь.",
            },
            {
                "title": "Ресторан с «меню для туристов»",
                "how": "Сверьте цену в меню и в чеке. Фото меню до заказа — ваш друг.",
            },
            {
                "title": "Такси кружным путём",
                "how": "Карта в телефоне открыта. Если едут «на море через Анкарy» — остановите.",
            },
            {
                "title": "Обмен у порта",
                "how": "Курс хуже банка. Меняйте в сети PTT/банка.",
            },
        ],
        "taste": [
            {"dish": "Симит", "where": "уличная тележка утром"},
            {"dish": "Дёнер / кебаб", "where": "очередь из местных, не витрина с подсветкой"},
            {"dish": "Баклава", "where": "кондитерская с весовым прилавком"},
            {"dish": "Чай в тюльпане", "where": "çay bahçesi у воды или во дворе"},
            {"dish": "Менemen", "where": "завтрак в простом lokanta"},
            {"dish": "Айран", "where": "к кебабу, везде"},
        ],
        "arrival": [
            "Деньги: банкомат, небольшая сумма в лирах.",
            "Связь: SIM в зале или eSIM до поездки.",
            "Вода: купите, особенно летом.",
            "Трансфер: Havaist/метро/приложение — не первого кричащего водителя.",
            "Якорь: магазин + аптека рядом с жильём.",
        ],
    },
    "eu": {
        "label": "Европа",
        "currency": "евро / местная",
        "emergency": [
            {"title": "Единый экстренный", "value": "112"},
            {"title": "Полиция (ориентир)", "value": "112"},
        ],
        "tips": [
            "Карта почти везде; наличные — мелочь на рынки.",
            "Чаевые: 5–10% или округление, в скандинавии часто уже включены.",
            "Транспорт: день/неделя pass обычно выгоднее разовых.",
            "Вода из-под крана в большинстве городов ЕС питьевая.",
        ],
        "taxi_line": "Please take me here / S'il vous plaît, amenez-moi ici",
        "phrases": [
            {"local": "Hello / Bonjour", "latin": "hello / bonjour", "ru": "Здравствуйте"},
            {"local": "Thank you / Merci", "latin": "thank you / merci", "ru": "Спасибо"},
            {"local": "How much?", "latin": "how much?", "ru": "Сколько стоит?"},
            {"local": "No, thank you", "latin": "no, thank you", "ru": "Нет, спасибо"},
            {"local": "Where is…?", "latin": "where is…?", "ru": "Где…?"},
            {"local": "Do you speak English?", "latin": "do you speak english?", "ru": "Вы говорите по-английски?"},
            {"local": "Delicious!", "latin": "delicious!", "ru": "Вкусно!"},
            {"local": "Help!", "latin": "help!", "ru": "Помогите!"},
        ],
        "traps": [
            {
                "title": "Петиции «на детей» у достопримечательностей",
                "how": "Пока читаете — второй человек лезет в сумку. «No, thank you» без остановки.",
            },
            {
                "title": "Кольцо на асфальте",
                "how": "Не поднимайте. Это классика отвлечения.",
            },
            {
                "title": "Ресторан с витриной у Эйфелевой / Колизея",
                "how": "Цена ×3 за посредственно. Отойдите на 2–3 улицы.",
            },
            {
                "title": "Фальшивые билеты у входа",
                "how": "Только официальная касса/сайт. Если «продам дешевле» — нет.",
            },
            {
                "title": "Бесплатный браслет",
                "how": "Надели — требуют деньги. Снимите и уходите.",
            },
        ],
        "taste": [
            {"dish": "Местный хлеб / выпечка", "where": "пекарня с очередью в 8 утра"},
            {"dish": "Рыночный сыр", "where": "крытый рынок, не сувенирная лавка"},
            {"dish": "Кофе по-местному", "where": "стойка, не сеть с английским меню на витрине"},
            {"dish": "Сезонное блюдо региона", "where": "bistrot / trattoria без фото-меню"},
            {"dish": "Уличное сладкое", "where": "киоск, где берут школьники"},
            {"dish": "Местное пиво/вино бокалом", "where": "бар без «tourist menu»"},
        ],
        "arrival": [
            "Деньги: карта + немного кэша на автомат билетов.",
            "Связь: eSIM или киоск; офлайн-карта скачана заранее.",
            "Билет: метро/RER/Flix — не такси «фикс прайс» у выхода.",
            "До жилья: проверьте зону билета (Париж — ловушка зон).",
            "Якорь: супермаркет + пекарня в радиусе 5 минут.",
        ],
    },
    "ru": {
        "label": "Россия",
        "currency": "рубль (RUB)",
        "emergency": [
            {"title": "Экстренный", "value": "112"},
            {"title": "Полиция", "value": "102"},
            {"title": "Скорая", "value": "103"},
        ],
        "tips": [
            "Карта и СБП везде; наличные почти не нужны.",
            "Такси: Яндекс/Ситимобил, не с руки у вокзала.",
            "Чаевые: по желанию, 5–10% в ресторане.",
        ],
        "taxi_line": "Пожалуйста, вот адрес — можно в навигаторе",
        "phrases": [
            {"local": "Здравствуйте", "latin": "zdravstvuyte", "ru": "Здравствуйте"},
            {"local": "Спасибо", "latin": "spasibo", "ru": "Спасибо"},
            {"local": "Сколько стоит?", "latin": "skolko stoit?", "ru": "Сколько стоит?"},
            {"local": "Нет, спасибо", "latin": "net, spasibo", "ru": "Нет, спасибо"},
            {"local": "Где…?", "latin": "gde…?", "ru": "Где…?"},
            {"local": "Помогите", "latin": "pomogite", "ru": "Помогите"},
            {"local": "Вкусно!", "latin": "vkusno!", "ru": "Вкусно!"},
            {"local": "Туалет?", "latin": "tualet?", "ru": "Туалет?"},
        ],
        "traps": [
            {
                "title": "Такси у аэропорта «официальное»",
                "how": "Часто дороже приложения в 2 раза. Заказывайте в телефоне.",
            },
            {
                "title": "Обменники у вокзала",
                "how": "Курс мусорный. Банкомат своего банка.",
            },
            {
                "title": "Экскурсия «только сегодня»",
                "how": "Давление срочностью. Сверьте отзывы и цену онлайн.",
            },
            {
                "title": "Кафе с меню без цен",
                "how": "Спросите до заказа. Молчат — уходите.",
            },
            {
                "title": "«Помогу с багажом»",
                "how": "Добровольцы потом требуют чаевые агрессивно. Отказ спокойный.",
            },
        ],
        "taste": [
            {"dish": "Местная выпечка", "where": "пекарня у дома, не фудкорт"},
            {"dish": "Столовая / кафе по подписке местных", "where": "очередь в обед"},
            {"dish": "Рынок", "where": "крытый рынок района"},
            {"dish": "Кофейня без пафоса", "where": "стойка, ноутбук-фри зона"},
            {"dish": "Региональный десерт", "where": "спросите у кассира «что берут чаще»"},
            {"dish": "Вечерний стритфуд", "where": "у парка, не у главного собора"},
        ],
        "arrival": [
            "Связь: обычно уже есть; проверьте офлайн-карты.",
            "Деньги: карта, кэш по желанию.",
            "Трансфер: приложение такси или аэроэкспресс.",
            "До жилья: адрес в буфере + подъезд/домофон.",
            "Якорь: Пятёрочка/Магнит + аптека.",
        ],
    },
    "default": {
        "label": "Универсально",
        "currency": "местная",
        "emergency": [{"title": "Экстренный (часто)", "value": "112 / 911"}],
        "tips": [
            "Сделайте фото паспорта отдельно от оригинала.",
            "Офлайн-карта и офлайн-переводчик до вылета.",
            "Такси — приложение, не «доброжелатель» у выхода.",
            "Чаевые: спросите у рецепции «как принято».",
        ],
        "taxi_line": "Please take me to this address",
        "phrases": [
            {"local": "Hello", "latin": "hello", "ru": "Здравствуйте"},
            {"local": "Thank you", "latin": "thank you", "ru": "Спасибо"},
            {"local": "How much?", "latin": "how much?", "ru": "Сколько?"},
            {"local": "No, thank you", "latin": "no, thank you", "ru": "Нет, спасибо"},
            {"local": "Where is…?", "latin": "where is…?", "ru": "Где…?"},
            {"local": "Help!", "latin": "help!", "ru": "Помогите!"},
            {"local": "Water", "latin": "water", "ru": "Вода"},
            {"local": "Bill, please", "latin": "bill, please", "ru": "Счёт, пожалуйста"},
        ],
        "traps": [
            {
                "title": "Слишком дружелюбный незнакомец",
                "how": "Если ведёт «в лучшее место» — вежливо нет и свой маршрут.",
            },
            {
                "title": "Помощь с багажом/билетом",
                "how": "Часто платная и агрессивная. Отказ без диалога.",
            },
            {
                "title": "Меню без цен",
                "how": "Цена до заказа или уход.",
            },
            {
                "title": "Обмен на улице",
                "how": "Только банк/официальный обменник.",
            },
            {
                "title": "«Сломанный» таксометр",
                "how": "Приложение или отказ от поездки.",
            },
        ],
        "taste": [
            {"dish": "Уличный завтрак местных", "where": "очередь в 8–9 утра"},
            {"dish": "Рыночная еда", "where": "прилавок, где берут с собой"},
            {"dish": "Фирменный напиток региона", "where": "не сувенирный киоск у достопримечательности"},
            {"dish": "Простое кафе без фото-меню", "where": "2–3 улицы от туристической оси"},
            {"dish": "Сладкое «как у бабушки»", "where": "пекарня / кондитерская с весом"},
            {"dish": "Вечерний стритфуд", "where": "парк / набережная, где гуляют местные"},
        ],
        "arrival": [
            "Деньги: банкомат в безопасной зоне терминала.",
            "Связь: eSIM/SIM до выхода в город.",
            "Вода и 10 минут тишины — не бегите сразу.",
            "Трансфер через приложение или официальную стойку.",
            "Якорь у жилья: магазин, аптека, понятный ориентир.",
        ],
    },
}

_QUEST_FALLBACK = [
    "Купи что-то съедобное там, где очередь из местных — не у главной площади.",
    "Спроси дорогу одной фразой на местном (хотя бы «где…?») и дойди без навигатора 5 минут.",
    "Найди двор / переулок без вывесок на английском и сделай одно фото «для себя».",
]


def _pack_for_trip(trip) -> tuple[str, Region, dict[str, Any]]:
    destination = extract_destination(trip.brief, trip.name)
    region = detect_region(destination)
    return destination, region, _PACKS[region]


def build_survival(trip) -> dict[str, Any]:
    destination, region, pack = _pack_for_trip(trip)
    return {
        "destination": destination,
        "region": region,
        "region_label": pack["label"],
        "currency": pack["currency"],
        "emergency": pack["emergency"],
        "tips": pack["tips"],
        "taxi_line": pack["taxi_line"],
        "phrases": pack["phrases"],
        "source": "rules",
    }


def build_traps(trip) -> dict[str, Any]:
    destination, region, pack = _pack_for_trip(trip)
    return {
        "destination": destination,
        "region": region,
        "traps": pack["traps"],
        "source": "rules",
    }


def build_taste(trip) -> dict[str, Any]:
    destination, region, pack = _pack_for_trip(trip)
    return {
        "destination": destination,
        "region": region,
        "items": pack["taste"],
        "source": "rules",
    }


def build_arrival(trip) -> dict[str, Any]:
    destination, region, pack = _pack_for_trip(trip)
    start = trip.start_date.isoformat() if trip.start_date else None
    return {
        "destination": destination,
        "region": region,
        "start_date": start,
        "steps": [
            {"n": i + 1, "text": text} for i, text in enumerate(pack["arrival"])
        ],
        "source": "rules",
    }


def build_quest_fallback(trip, day_index: int = 0) -> dict[str, Any]:
    destination, region, _pack = _pack_for_trip(trip)
    arts = {a.phase: a.content for a in trip.artifacts}
    itinerary = arts.get("itinerary", "")
    days = parse_itinerary_days(itinerary, start_date=trip.start_date)
    day = days[day_index] if 0 <= day_index < len(days) else None
    title = day["title"] if day else f"День {day_index + 1}"
    places = [s["place"] for s in (day or {}).get("slots") or []][:3]
    missions = list(_QUEST_FALLBACK)
    if places:
        missions[0] = (
            f"Возле «{places[0]}» найди еду/напиток без английской вывески и купи что-то маленькое."
        )
    if len(places) > 1:
        missions[2] = (
            f"Между «{places[0]}» и «{places[1]}» сверни в боковой проход и найди тихий кадр."
        )
    return {
        "destination": destination,
        "region": region,
        "day_index": day_index,
        "day_title": title,
        "missions": [{"id": i, "text": m} for i, m in enumerate(missions[:3])],
        "source": "rules",
    }


def parse_json_list(text: str, key: str) -> list | None:
    """Extract JSON object with key from LLM text."""
    text = (text or "").strip()
    if not text:
        return None
    # fenced json
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and key in data:
            return data[key]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # find first { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict) and key in data:
                return data[key]
        except json.JSONDecodeError:
            return None
    return None
