"""PII masking for text that is shown to people other than its author (US19 / US20).

Resolved requests are reused as "similar cases" for other students and as reply suggestions for
agents, so names, e-mails, phone numbers, ID numbers and request IDs are replaced by placeholders.
"""
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
PHONE = re.compile(r"(?<![\w+])(?:\+7|8)?[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\w)")
LONG_NUMBER = re.compile(r"(?<!\w)\d{6,}(?!\w)")  # IIN (12 digits), student / card numbers
REQUEST_ID = re.compile(r"\bREQ-\d{4}-\d{5}\b", re.IGNORECASE)
# "my name is Aruzhan Bekova", "меня зовут Дильназ", "менің атым Әлихан"
INTRO = re.compile(
    r"(?P<lead>\b(?i:my name is|i am|i'm|this is|меня зовут|менің атым|мен)\s+)"
    r"(?P<name>[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ][\w'-]+(?:\s+[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ][\w'-]+)?)",
    re.UNICODE,
)


def mask(text: str, names: list[str] | tuple[str, ...] = ()) -> str:
    """Replace PII with [email] / [phone] / [id] / [request] / [name]. `names` are known people to hide."""
    if not text:
        return ""
    out = EMAIL.sub("[email]", text)
    out = REQUEST_ID.sub("[request]", out)
    out = PHONE.sub("[phone]", out)
    out = LONG_NUMBER.sub("[id]", out)
    parts: set[str] = set()
    for n in names:
        if not n:
            continue
        parts.add(n.strip())
        parts.update(p for p in re.split(r"\s+", n.strip()) if len(p) >= 3 and not p.endswith("."))
    for p in sorted(parts, key=len, reverse=True):
        out = re.sub(rf"(?<!\w){re.escape(p)}(?!\w)", "[name]", out, flags=re.IGNORECASE)
    out = INTRO.sub(lambda m: m.group("lead") + "[name]", out)
    return re.sub(r"(\[name\])(\s+\[name\])+", r"\1", out)
