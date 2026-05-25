# PROJECT_LOG — Игровая база данных

> Этот файл ведётся совместно. В начале каждой новой сессии Claude читает его
> и продолжает с того места, где остановились.

---

## Стек (зафиксирован, не менять)

| Компонент | Версия | Роль |
|-----------|--------|------|
| Python | 3.13.1 | язык |
| Flask + Jinja2 | 3.1.1 | сервер + шаблоны |
| PostgreSQL | 17.10 | БД |
| psycopg 3 (binary) | 3.2.9 | драйвер, сырой SQL |
| python-dotenv | 1.1.0 | конфиг из .env |
| Werkzeug | 3.1.3 | хэширование паролей |

---

## Принятые архитектурные решения

- **Весь SQL — только в `db.py`**, в виде именованных функций. Маршруты Flask SQL не пишут.
- **Все запросы — параметризованные** (защита от SQL-инъекций).
- **Без ORM** — голый psycopg 3, это учебный проект по курсу «Базы данных».
- **Без Docker, без async, без blueprints** — один простой `app.py`.
- **Серверный рендеринг** через Jinja2, без отдельного фронтенда.
- **Пароли** хранятся только как хэши (Werkzeug), в коде паролей нет.
- **Конфиг** — только через `.env`, `.env.example` в репозитории, `.env` в `.gitignore`.

---

## Принципы безопасности (добавлено в сессии 2)

| Аспект | Решение |
|--------|---------|
| Роль БД | `gamedb_app` — только SELECT/INSERT/UPDATE/DELETE на таблицах приложения; без суперправ. SQL для создания в разделе «Как применить» ниже. |
| SECRET_KEY | `secrets.token_hex(32)`, хранится в `.env`, загружается через `os.getenv()`. |
| Сессионные куки | `HTTPONLY=True`, `SAMESITE=Lax`, `SECURE=False` на dev / `True` на prod (через `SESSION_COOKIE_SECURE` в `.env`). |
| Валидация | `validators.py`: `validate_username`, `validate_email`, `validate_password`, `validate_score`, `validate_search_query`. Возвращают строку-ошибку или `None`. |
| CSRF-токены | Добавим на этапе аутентификации. |
| Хэширование паролей | Используем Werkzeug `generate_password_hash` / `check_password_hash`. Реализация — на этапе `/register`. |
| Ошибки входа | При неудачном входе показывать **обобщённое** сообщение: «Неверный логин или пароль» — не раскрывать, что именно неверно. |

---

## Что было опробовано и оказалось неэффективным

| Проблема | Причина | Решение |
|----------|---------|---------|
| `python` не работал в терминале | Windows Store создала заглушку | Отключили псевдонимы в «Параметры → Приложения → Псевдонимы запуска» |
| `python` и `psql` не находились | Пути не в PATH | Добавили `Python313\`, `Python313\Scripts\`, `PostgreSQL\17\bin\` |
| `psql` не работал в новой сессии | PATH обновляется только для новых процессов | В каждом вызове добавляем `$env:Path = [Environment]::GetEnvironmentVariable(...)` |
| Пароль psql спрашивался интерактивно | psql требует ввода по умолчанию | Используем `$env:PGPASSWORD = "..."` перед вызовом |
| Дубль ссылки в game_store_links | Phase 2 SQL и seed_delta.sql оба вставили Dishonored | Дубль удалён; seed_delta.sql теперь с `NOT EXISTS`-проверкой |

---

## Структура проекта

```
проект БД/
├── app.py               # Flask-маршруты: /, /game/<id>, /search
├── db.py                # Слой БД: get_connection(), get_all_games(),
│                        #          get_game_by_id(), search_games()
├── validators.py        # Серверная валидация ввода
├── schema.sql           # DDL 12 таблиц (включая game_store_links)
├── seed.sql             # Канонические тестовые данные (8 игр, чистая БД)
├── seed_delta.sql       # Дельта: добавить к существующей БД (есть Dishonored)
├── requirements.txt     # Зафиксированные зависимости
├── .env                 # Конфиг (не в git)
├── .env.example         # Шаблон конфига
├── .gitignore
├── README.md
├── PROJECT_LOG.md       # Этот файл
├── templates/
│   ├── base.html        # Навигация, подвал
│   ├── index.html       # Каталог игр + форма поиска
│   ├── game.html        # Детальная страница игры
│   └── search.html      # Результаты поиска
├── static/
│   └── style.css        # Тёмная тема + стили для новых страниц
└── venv/                # Виртуальное окружение (не в git)
```

---

## Схема базы данных (12 таблиц)

### Каталог
- `developers(developer_id PK, name, country)`
- `publishers(publisher_id PK, name, country)`
- `platforms(platform_id PK, name UNIQUE)`
- `genres(genre_id PK, name UNIQUE)`
- `tags(tag_id PK, name UNIQUE)`
- `games(game_id PK, title, release_date, description, developer_id FK, publisher_id FK)`
- `game_platforms(game_id FK, platform_id FK)` — PK составной
- `game_genres(game_id FK, genre_id FK)` — PK составной
- `game_tags(game_id FK, tag_id FK)` — PK составной
- **`game_store_links(link_id PK, game_id FK CASCADE, store_name TEXT, url TEXT)`** ← новая

### Пользователи
- `users(user_id PK, username UNIQUE, email UNIQUE, password_hash, avatar_emoji, created_at)`
- `ratings(user_id FK, game_id FK, score CHECK 1..10, created_at)` — PK составной

### Заглушки (в schema.sql, закомментированы)
- `reviews`, `achievements`, `user_achievements`

---

## Текущее состояние проекта

**Этап: Каталог с поиском и карточками игр.**

- [x] Окружение настроено (Python 3.13, PostgreSQL 17, venv, PATH)
- [x] Git инициализирован, все фазы закоммичены
- [x] Безопасность: SESSION_COOKIE_HTTPONLY/SAMESITE/SECURE, SECRET_KEY из .env
- [x] `validators.py` готов для форм аутентификации
- [x] `schema.sql` применён (12 таблиц, включая `game_store_links`)
- [x] 8 игр в базе (Dishonored + Witcher 3 + Cyberpunk + Portal 2 + Dark Souls III + Hades + Hollow Knight + Sekiro)
- [x] Страница `/` — каталог с поиском, названия — ссылки
- [x] Страница `/game/<id>` — жанры, теги, платформы, оценка, кнопка «Купить»
- [x] Страница `/search?q=...` — поиск по названию (ILIKE)
- [x] Steam-ссылки для всех 8 игр в `game_store_links`

**Проверить вручную:**
1. `http://localhost:5000` — каталог 8 игр, форма поиска
2. Клик по «Dishonored» → `/game/1` (карточка + кнопка Steam)
3. Поиск «dark» → находит Dark Souls III и Dishonored нет (ищет по названию)
4. Поиск «cy» → находит Cyberpunk 2077

**Роль `gamedb_app`:** создать вручную (SQL ниже), затем сменить `DB_USER`/`DB_PASSWORD` в `.env`.

---

## Как создать роль gamedb_app

```sql
-- Запустить в psql -U postgres -d gamedb
-- Замените 'ВАШ_ПАРОЛЬ' на желаемый пароль

CREATE ROLE gamedb_app WITH LOGIN PASSWORD 'ВАШ_ПАРОЛЬ';

GRANT SELECT, INSERT, UPDATE, DELETE ON
    developers, publishers, platforms, genres, tags,
    games, game_platforms, game_genres, game_tags,
    users, ratings, game_store_links
TO gamedb_app;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO gamedb_app;
```

После создания обновите `.env`:
```
DB_USER=gamedb_app
DB_PASSWORD=ВАШ_ПАРОЛЬ
```

---

## Следующие шаги (в порядке приоритета)

### Ближайшие (следующая сессия)
1. **Регистрация и логин** — `/register`, `/login`, `/logout`, Flask-сессии, Werkzeug-хэши.
   Функции `db.create_user()`, `db.get_user_by_username()`.
2. **Оценки** — форма 1–10 на странице игры, `/rate/<game_id>`, `db.set_rating()`.
   Средняя оценка уже вычисляется в `get_game_by_id`.
3. **Рекомендации по тегам** — заглушка в `game.html` уже есть. JOIN по `game_tags`.

### Средняя очередь
4. Пагинация каталога (когда игр станет > 20).
5. Страница профиля пользователя.
6. Флэш-сообщения (Flask `flash`) для подтверждений.

### Поздняя очередь
7. `reviews` — текстовые отзывы.
8. `achievements` / `user_achievements`.

---

## Как запустить проект с нуля (для справки)

```powershell
# В папке проекта
venv\Scripts\activate
python app.py
# Открыть http://localhost:5000
```

База данных уже создана и заполнена (8 игр). Повторно применять SQL не нужно.

---

## История коммитов сессии 2

| Хэш | Сообщение |
|-----|-----------|
| `a980d5d` | `chore: initial project foundation` |
| `79c3109` | `feat: security hardening - session cookies, validators, secret key` |
| `e768715` | `feat: add game_store_links table and 8-game seed data` |
| `c68e5a2` | `feat: game detail page, search, updated catalog` |
