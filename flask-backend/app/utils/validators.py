"""Request parameter validation utilities"""

import re
from datetime import datetime, date
from typing import Any, Optional

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_required(data: dict, *fields: str) -> list[str]:
    return [f for f in fields if f not in data or data[f] is None or str(data[f]).strip() == ""]


def validate_pagination(page: Any, size: Any) -> tuple[int, int]:
    try:
        p = max(1, int(page or 1))
    except (TypeError, ValueError):
        p = 1
    try:
        s = max(1, min(int(size or 20), 100))
    except (TypeError, ValueError):
        s = 20
    return p, s


def validate_date_range(start: Optional[str], end: Optional[str]) -> tuple[bool, str]:
    if not start or not end:
        return False, "start_date and end_date are required"
    try:
        s = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        if s > e:
            return False, "start_date must be before or equal to end_date"
        return True, ""
    except ValueError:
        return False, "Dates must be in YYYY-MM-DD format"


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(_EMAIL_RE.match(email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8 or len(password) > 64:
        return False, "Password must be 8-64 characters"
    categories = 0
    if re.search(r"[A-Z]", password):
        categories += 1
    if re.search(r"[a-z]", password):
        categories += 1
    if re.search(r"\d", password):
        categories += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        categories += 1
    if categories < 3:
        return False, "Password must contain at least 3 of: uppercase, lowercase, digit, special character"
    return True, ""
