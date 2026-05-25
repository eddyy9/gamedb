"""
validators.py — серверная валидация входных данных.

Все функции возвращают строку с сообщением об ошибке
или None, если значение корректно.

Используется во всех формах приложения.
"""

import re
from typing import Optional

# ── Константы ────────────────────────────────────────────────
USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 50
PASSWORD_MIN_LEN = 8
EMAIL_MAX_LEN    = 255
SCORE_MIN        = 1
SCORE_MAX        = 10
SEARCH_MAX_LEN   = 200


# ── Пользователь ─────────────────────────────────────────────

def validate_username(username: str) -> Optional[str]:
    """Имя пользователя: длина, только [a-zA-Z0-9_-]."""
    if not username or not username.strip():
        return "Имя пользователя не может быть пустым."
    if len(username) < USERNAME_MIN_LEN:
        return f"Имя пользователя: минимум {USERNAME_MIN_LEN} символа."
    if len(username) > USERNAME_MAX_LEN:
        return f"Имя пользователя: максимум {USERNAME_MAX_LEN} символов."
    if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
        return "Имя пользователя может содержать только латиницу, цифры, _ и -."
    return None


def validate_email(email: str) -> Optional[str]:
    """Формат email: простая проверка наличия @ и домена."""
    if not email or not email.strip():
        return "Email не может быть пустым."
    if len(email) > EMAIL_MAX_LEN:
        return f"Email: максимум {EMAIL_MAX_LEN} символов."
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return "Неверный формат email."
    return None


def validate_password(password: str) -> Optional[str]:
    """Пароль: минимальная длина. Хэширование — только в db.py."""
    if not password:
        return "Пароль не может быть пустым."
    if len(password) < PASSWORD_MIN_LEN:
        return f"Пароль: минимум {PASSWORD_MIN_LEN} символов."
    return None


# ── Оценки ───────────────────────────────────────────────────

def validate_score(score) -> Optional[str]:
    """Оценка игры: целое число от 1 до 10."""
    try:
        score = int(score)
    except (TypeError, ValueError):
        return "Оценка должна быть целым числом."
    if score < SCORE_MIN or score > SCORE_MAX:
        return f"Оценка должна быть от {SCORE_MIN} до {SCORE_MAX}."
    return None


# ── Поиск ────────────────────────────────────────────────────

def validate_search_query(query: str) -> Optional[str]:
    """Строка поиска: только ограничение длины."""
    if query and len(query) > SEARCH_MAX_LEN:
        return f"Запрос поиска: максимум {SEARCH_MAX_LEN} символов."
    return None
