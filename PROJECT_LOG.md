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
- **Пароли** хранятся только как хэши (Werkzeug `generate_password_hash`), в коде паролей нет.
- **Конфиг** — только через `.env`, `.env.example` в репозитории, `.env` в `.gitignore`.
- **Текущий пользователь** — через `@app.context_processor` (inject_user): `current_user` доступен во всех шаблонах автоматически.

---

## Принципы безопасности

| Аспект | Решение |
|--------|---------|
| Роль БД | `gamedb_app` — только SELECT/INSERT/UPDATE/DELETE на таблицах приложения. SQL для создания — ниже. |
| SECRET_KEY | `secrets.token_hex(32)`, хранится в `.env`. |
| Сессионные куки | `HTTPONLY=True`, `SAMESITE=Lax`, `SECURE` через `.env` (false dev / true prod). |
| Хэширование паролей | Werkzeug `generate_password_hash` / `check_password_hash`. |
| Ошибка входа | Обобщённое «Неверный логин или пароль» — не раскрывает, что именно неверно. |
| Валидация | `validators.py`: username, email, password, score, search_query. |
| CSRF | Пока не добавлен — при добавлении форм расчётов добавить Flask-WTF или ручной CSRF-токен в сессии. |

---

## Что было опробовано и оказалось неэффективным

| Проблема | Причина | Решение |
|----------|---------|---------|
| `python` не работал в терминале | Windows Store-заглушка | Отключили псевдонимы запуска |
| `python`/`psql` не находились | Пути не в PATH | Добавили Python313, Scripts, PostgreSQL\17\bin |
| `psql` не работал в новой сессии | PATH только для новых процессов | `$env:Path = [Environment]::GetEnvironmentVariable(...)` |
| Пароль psql спрашивался интерактивно | psql требует ввода | `$env:PGPASSWORD = "..."` |
| Дубль ссылки в game_store_links | Phase 2 SQL и seed_delta оба вставили Dishonored | Дубль удалён; seed_delta с `NOT EXISTS`-проверкой |

---

## Структура проекта

```
проект БД/
├── app.py               # Flask-маршруты: /, /game/<id>, /search,
│                        #   /register, /login, /logout, /rate/<id>
├── db.py                # Слой БД: все SQL-функции
├── validators.py        # Серверная валидация ввода
├── schema.sql           # DDL 12 таблиц
├── seed.sql             # Канонические данные (8 игр, чистая БД)
├── seed_delta.sql       # Дельта для существующей БД
├── requirements.txt
├── .env                 # Конфиг (не в git)
├── .env.example
├── .gitignore
├── README.md
├── PROJECT_LOG.md
├── templates/
│   ├── base.html        # Навигация (user/login/register) + флэш
│   ├── index.html       # Каталог + поиск
│   ├── game.html        # Карточка игры, оценки, похожие игры
│   ├── search.html      # Результаты поиска
│   ├── register.html    # Форма регистрации
│   └── login.html       # Форма входа
└── static/
    └── style.css
```

---

## Функции db.py (актуальный список)

| Функция | Описание |
|---------|----------|
| `get_all_games()` | Все игры с dev/pub |
| `get_game_by_id(id)` | Карточка + жанры/теги/платформы/оценка/ссылки |
| `search_games(query)` | ILIKE по title |
| `create_user(u, e, ph)` | INSERT users, RETURNING user_id |
| `get_user_by_username(u)` | Для логина (включает password_hash) |
| `get_user_by_id(id)` | Для сессии (без хэша) |
| `set_rating(uid, gid, score)` | INSERT ON CONFLICT DO UPDATE |
| `get_user_rating(uid, gid)` | Оценка пользователя или None |
| `get_similar_games(gid, limit)` | JOIN по game_tags, ORDER BY shared_tags DESC |

---

## Схема базы данных (12 таблиц)

### Каталог
- `developers`, `publishers`, `platforms`, `genres`, `tags`
- `games(game_id PK, title, release_date, description, developer_id FK, publisher_id FK)`
- `game_platforms`, `game_genres`, `game_tags` — многие-ко-многим
- `game_store_links(link_id PK, game_id FK CASCADE, store_name, url)`

### Пользователи
- `users(user_id PK, username UNIQUE, email UNIQUE, password_hash, avatar_emoji, created_at)`
- `ratings(user_id FK, game_id FK, score CHECK 1..10, created_at)` — PK составной

---

## Текущее состояние проекта

**Этап: Каталог + Аутентификация + Оценки.**

- [x] Git инициализирован, 6 коммитов
- [x] 12 таблиц, 8 игр, Steam-ссылки
- [x] `/` — каталог, форма поиска
- [x] `/game/<id>` — карточка, оценки 1–10, похожие игры по тегам, кнопка «Купить»
- [x] `/search?q=...` — ILIKE-поиск
- [x] `/register`, `/login`, `/logout` — регистрация, вход, выход
- [x] `/rate/<id>` — оценка игры (только для авторизованных)
- [x] `current_user` во всех шаблонах через context_processor
- [x] Флэш-сообщения (success / error / info)

**Проверить вручную:**
1. Регистрация `/register` → автовход → флэш «Добро пожаловать!»
2. Выход → Войти `/login` → флэш «С возвращением»
3. Карточка игры → кнопки 1–10, нажать — оценка сохраняется (кнопка подсвечивается)
4. Средняя оценка в бейдже обновляется после следующего входа на страницу
5. Похожие игры: Dishonored → Dark Souls III, Hades, Hollow Knight, Sekiro (общие теги: dark, atmospheric)
6. Незалогиненный пользователь на `/game/<id>` видит «Войдите, чтобы оценить»

---

## Как создать роль gamedb_app (ещё не применено)

```sql
-- psql -U postgres -d gamedb
CREATE ROLE gamedb_app WITH LOGIN PASSWORD 'ВАШ_ПАРОЛЬ';
GRANT SELECT, INSERT, UPDATE, DELETE ON
    developers, publishers, platforms, genres, tags,
    games, game_platforms, game_genres, game_tags,
    users, ratings, game_store_links
TO gamedb_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO gamedb_app;
```

---

## Следующие шаги (в порядке приоритета)

### Ближайшие (следующая сессия)
1. **Страница профиля** `/profile` — список оценённых игр пользователя, дата регистрации.
2. **CSRF-защита** — добавить токен в формы (login, register, rate, logout) через скрытое поле + проверку в сессии. Или подключить Flask-WTF.
3. **Пагинация каталога** — когда игр больше 20 (сейчас 8, добавим).

### Средняя очередь
4. Фильтры каталога по жанру / платформе / тегу.
5. Текстовые отзывы (`reviews`).
6. Достижения (`achievements`).

---

## Как запустить

```powershell
venv\Scripts\activate
python app.py
# http://localhost:5000
```

---

## История коммитов

| Хэш | Сообщение |
|-----|-----------|
| `a980d5d` | `chore: initial project foundation` |
| `79c3109` | `feat: security hardening - session cookies, validators, secret key` |
| `e768715` | `feat: add game_store_links table and 8-game seed data` |
| `c68e5a2` | `feat: game detail page, search, updated catalog` |
| `9b43cf2` | `docs: update project log after session 2` |
| `80704bb` | `feat: user auth, ratings, similar games by tags` |
