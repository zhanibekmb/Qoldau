"""Hybrid urgency scorer (US6): category weight + editable keyword rules + date rules + ML confidence.

Score 0-100 -> Critical >= 80, High 60-79, Medium 35-59, Low < 35.
Keywords live in the urgency_keywords table, so the rule set is editable without redeploy.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from ..models import Priority, UrgencyKeyword

# Seed data for urgency_keywords: (keyword, weight, is_critical, language)
DEFAULT_KEYWORDS: list[tuple[str, int, bool, str]] = [
    # Critical: health / safety / harassment
    ("unsafe", 50, True, "en"), ("safety", 40, True, "en"), ("harass", 50, True, "en"),
    ("suicid", 60, True, "en"), ("assault", 60, True, "en"), ("violence", 50, True, "en"),
    ("emergency", 40, True, "en"), ("injur", 35, True, "en"), ("threat", 45, True, "en"),
    ("небезопасно", 50, True, "ru"), ("опасн", 40, True, "ru"), ("домога", 50, True, "ru"),
    ("насили", 60, True, "ru"), ("угрож", 45, True, "ru"), ("травм", 35, True, "ru"),
    ("қауіпсіз сезінбеймін", 50, True, "kz"), ("қауіп", 40, True, "kz"), ("зорлық", 60, True, "kz"),
    # High-weight signals
    ("deadline", 20, False, "en"), ("exam", 12, False, "en"), ("urgent", 20, False, "en"),
    ("asap", 15, False, "en"), ("blocked", 15, False, "en"), ("cannot pay", 20, False, "en"),
    ("fever", 20, False, "en"), ("unwell", 15, False, "en"), ("panic", 20, False, "en"),
    ("visa", 10, False, "en"), ("expires", 15, False, "en"), ("closes", 12, False, "en"),
    ("fails", 10, False, "en"), ("error", 8, False, "en"), ("not working", 8, False, "en"),
    ("broken", 8, False, "en"), ("locked", 10, False, "en"),
    ("срочно", 20, False, "ru"), ("дедлайн", 20, False, "ru"), ("срок", 12, False, "ru"),
    ("экзамен", 12, False, "ru"), ("не могу оплатить", 20, False, "ru"), ("температур", 20, False, "ru"),
    ("ошибк", 8, False, "ru"), ("не работает", 8, False, "ru"), ("заблокирован", 10, False, "ru"),
    ("шұғыл", 20, False, "kz"), ("тез", 10, False, "kz"), ("мерзім", 12, False, "kz"),
    ("емтихан", 12, False, "kz"), ("қате", 8, False, "kz"), ("жұмыс істемейді", 8, False, "kz"),
    # Low-urgency signals (information questions, feedback)
    ("feedback", -10, False, "en"), ("suggestion", -10, False, "en"), ("just wondering", -10, False, "en"),
    ("information", -5, False, "en"), ("отзыв", -10, False, "ru"), ("предложение", -10, False, "ru"),
    ("пікір", -10, False, "kz"),
]

TIME_RULES: list[tuple[re.Pattern, int, str]] = [
    (re.compile(r"\b(today|tonight|right now|immediately)\b|сегодня|сейчас|бүгін|қазір", re.I), 30, "due today"),
    (re.compile(r"\b(tomorrow|within 24|within 48|in two days)\b|завтра|послезавтра|ертең", re.I), 25,
     "due within 48 h"),
    (re.compile(r"\b(this week|next week)\b|на этой неделе|на следующей неделе|осы аптада|келесі аптада", re.I), 10,
     "due this/next week"),
]
DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b")


@dataclass
class UrgencyResult:
    priority: str
    score: int
    critical: bool
    reasons: list[str] = field(default_factory=list)


def score_to_priority(score: int) -> str:
    if score >= 80:
        return Priority.CRITICAL
    if score >= 60:
        return Priority.HIGH
    if score >= 35:
        return Priority.MEDIUM
    return Priority.LOW


def raise_one_level(priority: str) -> str:
    i = Priority.ORDER.index(priority)
    return Priority.ORDER[min(i + 1, len(Priority.ORDER) - 1)]


def _explicit_date_bonus(text: str, today: date) -> tuple[int, str | None]:
    for m in DATE_RE.finditer(text):
        d, mth, y = int(m.group(1)), int(m.group(2)), m.group(3)
        year = today.year if not y else (int(y) + 2000 if len(y) == 2 else int(y))
        try:
            when = date(year, mth, d)
        except ValueError:
            continue
        delta = (when - today).days
        if 0 <= delta <= 2:
            return 25, f"date {when.isoformat()} within 48 h"
    return 0, None


def score(db: Session, text: str, category_weight: int, workflow: str, ml_confidence: float = 1.0,
          now: datetime | None = None) -> UrgencyResult:
    lowered = text.lower()
    reasons: list[str] = [f"category weight +{category_weight}"]
    total = float(category_weight)
    critical = False

    keyword_points = 0
    for kw in db.query(UrgencyKeyword).all():
        if kw.keyword.lower() in lowered:
            keyword_points += kw.weight
            reasons.append(f'keyword "{kw.keyword}" {kw.weight:+d}')
            critical = critical or kw.is_critical
    total += max(-20, min(keyword_points, 50))

    time_points = 0
    for pattern, pts, label in TIME_RULES:
        if pattern.search(text):
            time_points = max(time_points, pts)
            reasons.append(f"{label} +{pts}")
    bonus, label = _explicit_date_bonus(text, (now or datetime.now()).date())
    if bonus:
        time_points = max(time_points, bonus)
        reasons.append(f"{label} +{bonus}")
    total += time_points

    # ML component: a confident classification adds a little weight, low confidence never lowers it below rules.
    total += round(5 * ml_confidence)

    result = int(max(0, min(100, round(total))))
    if critical:
        result = max(result, 85)
        reasons.append("critical keyword: forced Critical")
    elif workflow == "urgent":
        result = max(result, 60)
        reasons.append("urgent workflow: at least High")
    return UrgencyResult(score_to_priority(result), result, critical, reasons)
