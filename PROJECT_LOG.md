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
| Роль БД | `gamedb_app` — только SELECT/INSERT/UPDATE/DELETE на 11 таблицах каталога + users + ratings. **Применено:** приложение подключается под `gamedb_app` (не суперпользователь, без DDL-прав). Гранты: `CONNECT ON DATABASE gamedb`, `USAGE ON SCHEMA public`, DML на таблицах, `USAGE+SELECT ON ALL SEQUENCES`. Учётка `postgres` зарезервирована для DDL/миграций. |
| SECRET_KEY | `secrets.token_hex(32)`, хранится в `.env`. |
| Сессионные куки | `HTTPONLY=True`, `SAMESITE=Lax`, `SECURE` через `.env`. |
| Хэширование паролей | Werkzeug `generate_password_hash` / `check_password_hash`. |
| Ошибка входа | Обобщённое «Неверный логин или пароль» — не раскрывает, что именно неверно. |
| Валидация ввода | `validators.py`: username, email, password, score, search_query, safe_int. |
| **CSRF** | Реализован вручную через сессионный токен. `get_csrf_token()` генерирует `token_hex(32)` при первом рендере, сохраняет в `session["csrf_token"]`. Проверка в `@app.before_request` через `hmac.compare_digest` (постоянное время, защита от timing-атак). Токен прокидывается во все шаблоны через `inject_csrf` context_processor. Все POST-формы содержат скрытое поле `csrf_token`. GET-формы (поиск, фильтры) не проверяются. Flask-WTF не понадобился. |
| Фильтры по id | `safe_int()` в validators.py строго приводит к `int >= 1` или None; никакой склейки строк SQL. |

---

## Что было опробовано и оказалось неэффективным

| Проблема | Причина | Решение |
|----------|---------|---------|
| `python` не работал | Windows Store-заглушка | Отключили псевдонимы запуска |
| `python`/`psql` не находились | Пути не в PATH | Добавили Python313, Scripts, PostgreSQL\17\bin |
| `psql` не работал в новой сессии | PATH только для новых процессов | `$env:Path = [Environment]::GetEnvironmentVariable(...)` |
| Пароль psql спрашивался | psql требует ввода | `$env:PGPASSWORD = "..."` |
| Дубль ссылки в game_store_links | Phase 2 SQL и seed_delta оба вставили Dishonored | Дубль удалён; seed_delta с `NOT EXISTS` |
| `IndeterminateDatatype` при фильтре жанра + «Все теги» | PostgreSQL не может вывести тип `NULL` в `WHERE %s IS NULL` без контекста колонки | Заменить на `%s::int IS NULL` — явный каст даёт тип, логика сохраняется |

---

## Структура проекта

```
проект БД/
├── app.py               # Маршруты: /, /game/<id>, /search, /profile,
│                        #   /register, /login, /logout, /rate/<id>
│                        # CSRF: get_csrf_token(), check_csrf(), inject_csrf
├── db.py                # Весь SQL: 12 функций
├── validators.py        # Валидация: 6 функций + safe_int
├── schema.sql           # DDL 12 таблиц
├── seed.sql             # Канонические данные (8 игр, чистая БД)
├── seed_delta.sql       # Дельта для существующей БД
├── requirements.txt
├── .env / .env.example / .gitignore / README.md / PROJECT_LOG.md
├── templates/
│   ├── base.html        # Nav (user -> /profile | login/reg) + flash + CSRF logout
│   ├── index.html       # Каталог + поиск + фильтры жанр/тег
│   ├── game.html        # Карточка + оценки + похожие + CSRF rate
│   ├── search.html      # Результаты поиска
│   ├── profile.html     # Профиль: статистика + список оценённых игр
│   ├── register.html    # Форма + CSRF
│   └── login.html       # Форма + CSRF
└── static/style.css
```

---

## Функции db.py (актуальный список)

| Функция | Описание |
|---------|----------|
| `get_all_games()` | Все игры с dev/pub |
| `get_game_by_id(id)` | Карточка + жанры/теги/платформы/оценка/ссылки |
| `search_games(query)` | ILIKE по title |
| `get_all_genres()` | Все жанры для фильтра |
| `get_all_tags()` | Все теги для фильтра |
| `get_games_filtered(genre_id, tag_id)` | LEFT JOIN с ON-фильтром + WHERE IS NULL-трюк |
| `create_user(u, e, ph)` | INSERT users, RETURNING user_id |
| `get_user_by_username(u)` | Для логина (password_hash включён) |
| `get_user_by_id(id)` | Для сессии (без хэша, включает created_at) |
| `get_user_ratings(uid)` | Оценённые игры, ORDER BY score DESC |
| `get_user_stats(uid)` | COUNT + ROUND AVG оценок |
| `set_rating(uid, gid, score)` | INSERT ON CONFLICT DO UPDATE |
| `get_user_rating(uid, gid)` | Оценка пользователя для одной игры |
| `get_similar_games(gid, limit)` | JOIN по game_tags, ORDER BY shared_tags DESC |
| `get_global_top(limit, exclude_user_id)` | Игры с наивысшим AVG(score). `exclude_user_id` — NOT EXISTS по ratings, исключает оценённые игры залогиненного пользователя; None → чистый топ для гостя |
| `get_recommendations(uid, limit)` | CTE taste/candidates/scored (tag-affinity = AVG−5.5); cold start → global top (с exclude_user_id); padding тоже через get_global_top(exclude_user_id); поле source='personal'\|'global' |

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

## Идеи рекомендаций

### 1. ✅ Персональные рекомендации на главной (реализовано в сессии 5)

**Реализовано:**
- `get_global_top(limit)` — глобальный топ по AVG(score) от всех пользователей.
- `get_recommendations(user_id, limit)` — tag-affinity CTE (taste/candidates/scored).
  - affinity = `AVG(score) - 5.5` по каждому тегу (центрирование относительно нейтральной оценки).
  - cold start: < 3 оценок → global top (source='global').
  - padding: если personal < limit, дополняем global top, исключая уже показанные и оценённые.
- Блок «Рекомендуем вам» на `/` — выше каталога. Подпись меняется по source.
- Гостям — global top с пометкой «Популярное сейчас».

**Идея для улучшения:** вместо фиксированного `5.5` использовать персональный средний балл пользователя — центрирование вокруг его собственного среднего сделает affinity более точным.

### 2. «Что-то новое» — исследование слепых зон

**Идея:** показывать жанры/теги, в которых пользователь ещё не оценивал игры (или оценивал мало), и выводить хорошо оценённые **другими** игры оттуда.

- **Дёшевая версия** (только ratings, новых таблиц нет): `LEFT JOIN` через `ratings` пользователя → найти теги без оценок → лучшие чужие оценки.
- **Версия с кликами:** потребует отдельной таблицы-журнала просмотров/кликов (`game_views`). Отложено — добавит нагрузку на БД и нужна отдельная оценка целесообразности.

---

## Текущее состояние проекта

**Этап: Каталог + Аутентификация + Оценки + Профиль + CSRF + Фильтры + Рекомендации + Роль БД.**

- [x] Git: 15 коммитов
- [x] 12 таблиц, 8 игр, Steam-ссылки
- [x] `/` — каталог с поиском, фильтрами (жанр/тег) и блоком рекомендаций
- [x] `/game/<id>` — карточка, оценки 1–10, похожие игры, кнопка «Купить»
- [x] `/search?q=...` — ILIKE-поиск
- [x] `/register`, `/login`, `/logout` — полная аутентификация
- [x] `/rate/<id>` — оценка (только авторизованным)
- [x] `/profile` — статистика, список оценённых игр
- [x] CSRF: сессионный токен + `hmac.compare_digest` в `before_request`
- [x] Фильтры каталога: жанр + тег (параметризованный SQL, `safe_int`)
- [x] Персональные рекомендации: tag-affinity CTE + cold start fallback
- [x] Роль БД: приложение подключается под `gamedb_app` (только DML, без DDL, не суперпользователь)

**Проверить вручную:**
1. `/` → фильтр «RPG» → 4 игры (Witcher 3, Cyberpunk, Dark Souls III, Hades)
2. `/` → фильтр «RPG» + тег «dark» → 2 игры (Witcher 3, Dark Souls III)
3. `/` → редкий тег → «По выбранным фильтрам ничего не найдено»
4. Зарегистрироваться → оценить 3 игры → `/profile` → статистика обновилась
5. Попытка POST без CSRF (curl/Postman) → HTTP 400
6. `/profile` без входа → redirect на `/login` с флэшем
7. `/` без входа → блок «Популярное сейчас» (global top, до 4 карточек)
8. Войти → оценить < 3 игр → `/` → блок показывает НЕоценённые популярные игры (source=global)
9. Войти → оценить ≥ 3 игр → `/` → блок «На основе ваших оценок» (personal), оценённых нет
10. Войти → оценить все 8 игр → `/` → блок рекомендаций пуст (нечего рекомендовать)
11. Войти → оценить Witcher 3 и Dark Souls III → `/` → этих двух игр НЕТ в блоке рекомендаций
12. `psql -U gamedb_app -d gamedb -c "CREATE TABLE test_forbidden(id int);"` → `ERROR: permission denied` (DDL запрещён)

---

## Роль gamedb_app (применено в сессии 7)

Роль создана и приложение переведено на неё. Учётка `postgres` — только для DDL/миграций.

```sql
-- Выполнено под postgres:
CREATE ROLE gamedb_app WITH LOGIN PASSWORD '...';         -- не суперпользователь
GRANT CONNECT ON DATABASE gamedb TO gamedb_app;
GRANT USAGE ON SCHEMA public TO gamedb_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    developers, publishers, platforms, genres, tags,
    games, game_platforms, game_genres, game_tags,
    users, ratings, game_store_links
TO gamedb_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gamedb_app;
-- Нет: SUPERUSER, CREATE, DROP, ALTER, TRUNCATE
```

Проверено: SELECT (каталог, карточка, поиск), INSERT + sequence (регистрация),
SELECT (профиль, рекомендации), INSERT ON CONFLICT (оценка) — всё без `permission denied`.

---

## Следующие шаги (в порядке приоритета)

### Ближайшие (следующая сессия)
1. **Пагинация каталога** — нужна, когда игр > 20 (сейчас 8, можно добавить ещё).

### Средняя очередь
3. Текстовые отзывы (`reviews`): форма на `/game/<id>`, таблица, вывод под описанием.
4. Сортировка каталога (по дате, по оценке, по названию).
5. Достижения (`achievements`).

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
| `ffeb444` | `docs: update project log after session 3` |
| `e68db51` | `feat: user profile page /profile` |
| `6d3c907` | `feat: CSRF protection via session token + before_request` |
| `2bc9dce` | `feat: catalog filters by genre and tag` |
| `e9b0565` | `fix: IndeterminateDatatype in get_games_filtered` |
| `6688623` | `feat: personalized recommendations on main page` |
| `2ce267b` | `docs: update project log after session 5 (recommendations)` |
| `6b61128` | `fix: exclude already-rated games from recommendation fallback` |
| `5240477` | `docs: update project log after session 6 (recommendation fix)` |
| — | `feat: connect app under least-privilege role gamedb_app` |
