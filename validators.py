"""
validators.py — серверная валидация входных данных.

Все функции возвращают строку с сообщением об ошибке
или None, если значение корректно.

Используется во всех формах приложения.
"""

import datetime
import re
from typing import List, Optional

# ── Константы ────────────────────────────────────────────────
USERNAME_MIN_LEN  = 3
USERNAME_MAX_LEN  = 50
PASSWORD_MIN_LEN  = 8
EMAIL_MAX_LEN     = 255
SCORE_MIN         = 1
SCORE_MAX         = 10
SEARCH_MAX_LEN    = 200
GAME_TITLE_MAX_LEN = 300


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


# ── Фильтры (безопасное приведение к int) ────────────────────

def safe_int(value, min_val: int = 1) -> Optional[int]:
    """Преобразует входящее значение в int >= min_val.
    Возвращает None при любой ошибке или если значение < min_val.
    Используется для id-параметров из URL-строки запроса.
    """
    try:
        v = int(value)
        return v if v >= min_val else None
    except (TypeError, ValueError):
        return None


# ── Форма добавления игры ─────────────────────────────────────

def validate_game_title(title: str) -> Optional[str]:
    """Название игры: непустое, максимальная длина совпадает со схемой БД."""
    if not title or not title.strip():
        return "Название игры не может быть пустым."
    if len(title) > GAME_TITLE_MAX_LEN:
        return f"Название игры: максимум {GAME_TITLE_MAX_LEN} символов."
    return None


def validate_release_date(date_str: str) -> Optional[str]:
    """Дата выхода: формат YYYY-MM-DD (стандартный ISO, принимается PostgreSQL DATE)."""
    try:
        datetime.date.fromisoformat(date_str)
        return None
    except (ValueError, TypeError):
        return "Неверный формат даты. Ожидается YYYY-MM-DD (например, 2015-05-19)."


def parse_new_names(raw: str) -> List[str]:
    """Парсит строку с именами через запятую.

    Для каждого элемента: обрезает пробелы, отбрасывает пустые строки,
    убирает дубликаты внутри одного запроса (сохраняет порядок первого
    появления). Возвращает список строк.

    Пример: "  RPG , Roguelike, rpg" → ["RPG", "Roguelike"]
    (сравнение без учёта регистра для дедупликации)
    """
    if not raw:
        return []
    seen: set = set()
    result: List[str] = []
    for part in raw.split(","):
        name = part.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result
