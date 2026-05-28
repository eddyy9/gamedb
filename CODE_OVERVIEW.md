# CODE_OVERVIEW — разбор проекта «Игровая база данных»

> Этот документ — путеводитель по реальному коду проекта. Он написан так,
> чтобы автор мог уверенно отвечать на устной защите: что делает каждый
> файл, как идёт запрос «от браузера до PostgreSQL и обратно», какие
> приёмы применены и почему. Ничего не выдумано — все факты получены
> чтением `app.py`, `db.py`, `validators.py`, `schema.sql`, `seed.sql`,
> `seed_delta.sql`, шаблонов и `requirements.txt`.

---

## 1. КАРТА ФАЙЛОВ

| Файл | За что отвечает |
|------|------|
| `app.py` | Flask-приложение: маршруты, сессии, CSRF, декоратор `admin_required`, context-процессоры (`current_user`, `csrf_token`). SQL не пишет — только вызывает функции из `db.py`. |
| `db.py` | Весь SQL проекта. Подключение к БД через psycopg 3 (`get_connection`), 24 функции для чтения и записи. Транзакционные `create_game` и `update_game`. |
| `validators.py` | Серверная валидация ввода: username, email, password, score, search_query, game_title, release_date, `safe_int`, `parse_new_names`. Каждая функция возвращает строку ошибки или `None`. |
| `schema.sql` | DDL 12 таблиц: справочники (developers, publishers, platforms, genres, tags), `games`, связующие `game_platforms` / `game_genres` / `game_tags`, `game_store_links`, `users`, `ratings`. |
| `seed.sql` | Канонические тестовые данные на чистую БД: 6 разработчиков, 6 издателей, 5 платформ, 5 жанров, 11 тегов, 8 игр со всеми связями и Steam-ссылками. |
| `seed_delta.sql` | Дельта-сид: добавляет недостающие записи к уже существующей БД (если когда-то применялся только частичный `seed.sql`). Использует `ON CONFLICT DO NOTHING` и `NOT EXISTS`, чтобы не плодить дубли. |
| `requirements.txt` | Зафиксированные версии: Flask 3.1.1, psycopg[binary] 3.2.9, python-dotenv 1.1.0, werkzeug 3.1.3. |
| `templates/base.html` | Базовый шаблон: навбар (с кнопками «🛠 Добавить игру» только для `is_admin`, профиль, выход), флэш-сообщения, подвал. |
| `templates/index.html` | Главная: блок рекомендаций (персональные/глобальные), форма поиска, фильтры жанр+тег, сетка карточек игр. |
| `templates/game.html` | Карточка игры: заголовок (с кнопкой «✏️ Редактировать» для админа), бейдж средней оценки, мета-строка, платформы/жанры/теги, описание, форма оценки 1–10, ссылки на магазины, похожие игры по тегам. |
| `templates/search.html` | Страница результатов поиска по названию (ILIKE). |
| `templates/profile.html` | Профиль: аватар, дата регистрации, статистика (сколько оценено, средняя оценка), список оценённых игр. |
| `templates/register.html` | Форма регистрации (username, email, password) + скрытое поле `csrf_token`. |
| `templates/login.html` | Форма входа (username, password) + скрытое поле `csrf_token`. |
| `templates/admin_add_game.html` | Админская форма создания игры: основные поля, выбор существующего dev/pub + текстовое поле «или ввести нового», чекбоксы жанров/тегов/платформ + поля «новые через запятую». |
| `templates/admin_edit_game.html` | Та же структура, но предзаполненная: `value=` в текстовых полях, `selected` в `<select>`, `checked` в чекбоксах для текущих жанров/тегов/платформ. |
| `static/style.css` | Стили. |
| `PROJECT_LOG.md` | Журнал проекта: стек, решения, история коммитов. |
| `README.md`, `.env`, `.env.example`, `.gitignore` | Конфигурация и базовая документация. |

---

## 2. ПОТОК ЗАПРОСА END-TO-END

Здесь мы прослеживаем два конкретных запроса полностью: что делает
браузер, какой маршрут Flask вызывается, какая функция в `db.py`
выполняется, какие SQL-запросы уходят в PostgreSQL, как результат
возвращается обратно в Jinja и что в итоге видит пользователь.

### Пример 2.1. Открытие страницы игры `/game/<id>`

**Шаг 1 — Браузер.**
Пользователь кликает на ссылку «Dishonored» в каталоге. Браузер шлёт
`GET /game/1`.

**Шаг 2 — Flask маршрутизация.**
Срабатывает `app.py`:
- `@app.before_request → check_csrf()` — это GET, проверка пропускается.
- `@app.context_processor → inject_user()` — читает `session["user_id"]`,
  если есть, дёргает `db.get_user_by_id(uid)` и кладёт в шаблонный
  контекст `current_user`.
- `@app.context_processor → inject_csrf()` — генерирует/достаёт
  `csrf_token` из сессии, кладёт в шаблонный контекст.
- `@app.route("/game/<int:game_id>") def game_detail(game_id)`.

**Шаг 3 — `app.py:game_detail` вызывает `db.py`.**
```python
game = db.get_game_by_id(game_id)        # см. шаг 4
if game is None: abort(404)
user_rating = None
user_id = session.get("user_id")
if user_id:
    user_rating = db.get_user_rating(user_id, game_id)
similar = db.get_similar_games(game_id, limit=4)
return render_template("game.html",
                       game=game, user_rating=user_rating, similar=similar)
```

**Шаг 4 — `db.get_game_by_id` уходит в PostgreSQL.**
Функция открывает одно соединение через context manager и выполняет
четыре (плюс одно опциональное) параметризованных SELECT-а:

1. Главный запрос: `JOIN games ↔ developers ↔ publishers ↔ ratings`,
   `GROUP BY` по идентификаторам игры/dev/pub,
   `ROUND(AVG(r.score), 1) AS avg_score`, `COUNT(r.score) AS ratings_count`.
   Если строка не нашлась — возвращается `None`.
2. Жанры этой игры: `JOIN game_genres + genres WHERE game_id=%s`.
3. Теги: аналогично через `game_tags + tags`.
4. Платформы: через `game_platforms + platforms`.
5. Ссылки на магазины: `SELECT store_name, url FROM game_store_links
   WHERE game_id=%s`. Обёрнуто в `try/except` — если таблицы нет, в
   результате будет пустой список.

Все запросы параметризованы (`%s`), значения передаются кортежем —
никакого склеивания строк.

**Шаг 5 — Возврат в Python.**
`dict_row` (psycopg 3 row factory из `db.get_connection`) превращает
каждую строку в `dict`. Функция собирает финальный словарь:
```python
{
  "game_id": 1, "title": "Dishonored",
  "release_date": date(2012, 10, 9),
  "description": "...",
  "developer": "Arkane Studios", "developer_country": "France",
  "publisher": "Bethesda Softworks", "publisher_country": "USA",
  "avg_score": Decimal("8.5"), "ratings_count": 4,
  "genres": ["Action", "Stealth"],
  "tags": ["dark", "steampunk", "story-rich"],
  "platforms": ["PC", "PlayStation 4", "Xbox One"],
  "store_links": [{"store_name": "Steam", "url": "..."}]
}
```

**Шаг 6 — Jinja2 рендерит `game.html`.**
- Если `current_user.is_admin` — отрисовывается ссылка
  «✏️ Редактировать» на `/admin/edit_game/<id>`.
- Если `game.avg_score` — рисуется бейдж со средней оценкой и
  числом оценок (со склонением «оценка/оценки/оценок»).
- Перебираются `game.platforms`, `game.genres`, `game.tags` —
  каждая вещь становится `<span class="tag …">`.
- Если `current_user` — рисуется форма оценки с 10 кнопками
  (1…10), скрытым `csrf_token` и подсветкой `active` для уже
  поставленной оценки (`user_rating`). Иначе — приглашение войти.
- Перебираются `game.store_links` — кнопки «🛒 Где купить».
- Перебираются `similar` (до 4 карточек), показывается число
  общих тегов со склонением.

**Шаг 7 — HTML летит в браузер.** Готово.

---

### Пример 2.2. Блок «Рекомендуем вам» на главной

**Шаг 1 — Браузер.** Пользователь открывает `/` (он залогинен).

**Шаг 2 — `app.py:index`.**
```python
genre_id = safe_int(request.args.get("genre_id"))   # → None
tag_id   = safe_int(request.args.get("tag_id"))     # → None
games = db.get_all_games()                          # каталог
genres = db.get_all_genres()                        # для фильтра
tags   = db.get_all_tags()                          # для фильтра
user_id = session.get("user_id")
if user_id:
    recommendations = db.get_recommendations(user_id, limit=4)
else:
    recommendations = [dict(r, source="global")
                       for r in db.get_global_top(limit=4)]
return render_template("index.html", games=…, recommendations=…, …)
```

**Шаг 3 — `db.get_recommendations(user_id, 4)` принимает решение
о «холодном старте».**
Сначала отдельный счётчик:
```sql
SELECT COUNT(*) AS cnt FROM ratings WHERE user_id = %s;
```
- Если `cnt < 3` → вызываем `get_global_top(4, exclude_user_id=user_id)`
  и помечаем все строки `source='global'`.
- Если `cnt ≥ 3` → запускаем «персональный» SQL с CTE.

**Шаг 4 — Персональный SQL (один запрос, три CTE).**
```sql
WITH taste AS (
    SELECT gt.tag_id, AVG(r.score) - 5.5 AS affinity
    FROM ratings r
    JOIN game_tags gt ON gt.game_id = r.game_id
    WHERE r.user_id = %s
    GROUP BY gt.tag_id
),
candidates AS (
    SELECT g.game_id FROM games g
    WHERE NOT EXISTS (
        SELECT 1 FROM ratings r
        WHERE r.user_id = %s AND r.game_id = g.game_id
    )
),
scored AS (
    SELECT c.game_id, SUM(t.affinity) AS rec_score
    FROM candidates c
    JOIN game_tags gt ON gt.game_id = c.game_id
    JOIN taste     t  ON t.tag_id   = gt.tag_id
    GROUP BY c.game_id
)
SELECT g.game_id, g.title, d.name AS developer, s.rec_score
FROM scored s
JOIN games g ON g.game_id = s.game_id
LEFT JOIN developers d USING (developer_id)
ORDER BY s.rec_score DESC
LIMIT %s;
```

Что делает каждый CTE простыми словами:

- **`taste`** — «вкус пользователя по тегам». Берёт все его оценки,
  присоединяет теги тех игр и считает среднюю оценку по каждому тегу,
  смещая её на –5.5. Получается число: положительное — тег
  ему обычно нравится, отрицательное — обычно не нравится.
  Это и есть **affinity**, степень любви к тегу.
- **`candidates`** — игры, которые пользователь **ещё не оценивал**
  (через `NOT EXISTS`).
- **`scored`** — для каждой игры-кандидата складываем affinity всех
  её тегов. Чем больше «любимых» тегов у игры — тем выше итоговый
  `rec_score`.

Финальный `SELECT` присоединяет название игры и разработчика и
сортирует по `rec_score DESC`, отдавая `LIMIT 4`.

**Шаг 5 — Дополнение глобальным топом (padding).**
Если персональных вернулось меньше 4 (например, у пользователя
только 3 оценки и кандидатов мало), функция добивает остаток через
`get_global_top(limit + len(shown_ids), exclude_user_id=user_id)`
и фильтрует в Python уже показанные игры:
```python
shown_ids = {r["game_id"] for r in personal}
top_rows = get_global_top(limit + len(shown_ids), exclude_user_id=user_id)
padding = [dict(r, source="global")
           for r in top_rows
           if r["game_id"] not in shown_ids][:need]
return personal + padding
```
Каждой строке проставляется `source = 'personal' | 'global'`.

**Шаг 6 — `get_global_top` (используется и при холодном старте,
и для padding).**
```sql
SELECT g.game_id, g.title, d.name AS developer,
       ROUND(AVG(r.score), 1) AS avg_score,
       COUNT(r.score)         AS ratings_count
FROM games g
JOIN ratings r USING (game_id)
LEFT JOIN developers d USING (developer_id)
WHERE (%(uid)s::int IS NULL OR NOT EXISTS (
    SELECT 1 FROM ratings r2
    WHERE r2.game_id = g.game_id AND r2.user_id = %(uid)s
))
GROUP BY g.game_id, g.title, d.name
ORDER BY avg_score DESC, ratings_count DESC
LIMIT %(limit)s;
```
Приём `%(uid)s::int IS NULL` — явное приведение к типу даёт
PostgreSQL понять тип параметра, когда он `NULL` (см. раздел 7).

**Шаг 7 — Jinja2 рендерит блок в `index.html`.**
```jinja
{% if recommendations %}
<section class="recommendations">
  <h2>🎮 Рекомендуем вам
      <span class="rec-subtitle">
          {% if recommendations[0].source == 'personal' %}
              — На основе ваших оценок
          {% else %}
              — Популярное сейчас
          {% endif %}
      </span>
  </h2>
  ...
```
Подпись блока меняется по `source` первой карточки; для каждой
карточки выводится либо «✨ лично для вас», либо «⭐ avg / 10».

---

## 3. РАЗБОР `db.py`

`db.py` — это единственное место, где живёт SQL. Каждая функция
открывает соединение через `get_connection()` (psycopg 3,
`row_factory=dict_row`), выполняет один или несколько
**параметризованных** запросов и закрывает соединение через
context manager `with conn:`.

Подключение читает параметры из `.env`:
```python
psycopg.connect(host=…, port=…, dbname=…, user=…, password=…,
                row_factory=dict_row)
```
В .env прописана учётка `gamedb_app` (см. раздел 6).

### 3.1 Каталог

#### `get_all_games()`
- **Назначение:** список всех игр для каталога.
- **SQL:** `SELECT g.* + d.name AS developer + p.name AS publisher
  FROM games g LEFT JOIN developers d USING (developer_id)
  LEFT JOIN publishers p USING (publisher_id) ORDER BY g.title`.
- **Принимает:** ничего.
- **Возвращает:** список словарей с полями `game_id, title,
  release_date, description, developer, publisher`.
- **Ключевой приём:** `LEFT JOIN` — игра показывается, даже если
  у неё нет dev/pub. `USING (developer_id)` — короче и понятнее
  чем `ON g.developer_id = d.developer_id`.

#### `get_game_by_id(game_id)`
- **Назначение:** полная карточка игры для `/game/<id>`.
- **SQL:** четыре последовательных запроса в одном курсоре:
  1) главный с агрегатом `AVG/COUNT` по `ratings`;
  2) `game_genres + genres`;
  3) `game_tags + tags`;
  4) `game_platforms + platforms`;
  5) `game_store_links` (под `try/except` — на случай отсутствия таблицы).
- **Принимает:** `game_id`.
- **Возвращает:** один словарь со всеми связанными списками или `None`.
- **Ключевой приём:** соединение `LEFT JOIN ratings + GROUP BY`
  даёт среднюю оценку прямо в одном запросе; коллекции (жанры/теги/
  платформы) собираются отдельными простыми запросами — это понятнее,
  чем один монстр с подзапросами или массивами.

#### `search_games(query)`
- **Назначение:** поиск по названию.
- **SQL:** `WHERE g.title ILIKE %s` с `"%query%"`.
- **Ключевой приём:** **параметризация** — строка пользователя
  никогда не склеивается в SQL, ILIKE без учёта регистра.

#### `get_all_genres()` / `get_all_tags()` / `get_all_developers()` / `get_all_publishers()` / `get_all_platforms()`
- **Назначение:** справочники для выпадающих списков (фильтры
  каталога и админ-формы).
- **SQL:** `SELECT id, name FROM <table> ORDER BY name`.
- **Возвращает:** список словарей.

#### `get_games_filtered(genre_id=None, tag_id=None)`
- **Назначение:** каталог с фильтром по жанру и/или тегу.
- **SQL:**
  ```sql
  SELECT DISTINCT g.*, d.name AS developer, p.name AS publisher
  FROM games g
  LEFT JOIN developers d USING (developer_id)
  LEFT JOIN publishers p USING (publisher_id)
  LEFT JOIN game_genres gg ON g.game_id = gg.game_id AND gg.genre_id = %s
  LEFT JOIN game_tags   gt ON g.game_id = gt.game_id AND gt.tag_id   = %s
  WHERE (%s::int IS NULL OR gg.genre_id IS NOT NULL)
    AND (%s::int IS NULL OR gt.tag_id   IS NOT NULL)
  ORDER BY g.title;
  ```
- **Ключевой приём 1:** условие `gg.genre_id = %s` стоит в `ON`,
  не в `WHERE`. Это значит: для игр без подходящей пары `LEFT JOIN`
  даст `NULL`, и затем `WHERE … IS NOT NULL` отсечёт их. Если
  фильтр не задан (`NULL`), весь `WHERE` пропускает строку.
- **Ключевой приём 2:** `%s::int IS NULL` — явный каст. Без него
  PostgreSQL не мог вывести тип параметра-NULL и падал на
  `IndeterminateDatatype` (см. PROJECT_LOG, исправление коммитом
  `e9b0565`).

### 3.2 Пользователи и оценки

#### `create_user(username, email, password_hash)`
- **SQL:** `INSERT INTO users (username, email, password_hash)
  VALUES (%s,%s,%s) RETURNING user_id`.
- **Возвращает:** новый `user_id`.
- **Замечание:** при дубликате имени/email кидает
  `psycopg.errors.UniqueViolation` — её ловит `app.py:register`.

#### `get_user_by_username(username)`
- **SQL:** `SELECT user_id, username, email, password_hash,
  avatar_emoji, is_admin FROM users WHERE username = %s`.
- **Используется в `/login`:** возвращает хэш и флаг админа.

#### `get_user_by_id(user_id)`
- **SQL:** то же без `password_hash`, с `created_at`.
- **Используется в `inject_user` и `admin_required`:** даёт
  `current_user` во все шаблоны и проверяет `is_admin` для
  доступа к админ-разделу.

#### `set_rating(user_id, game_id, score)`
- **SQL:**
  ```sql
  INSERT INTO ratings (user_id, game_id, score)
  VALUES (%s, %s, %s)
  ON CONFLICT (user_id, game_id)
  DO UPDATE SET score = EXCLUDED.score, created_at = now();
  ```
- **Ключевой приём:** **`ON CONFLICT DO UPDATE`** (upsert).
  Один запрос делает «вставить или, если уже есть, обновить».
  `EXCLUDED.score` — это значение, которое мы пытались вставить.
  Не нужно сначала SELECT-ить, а потом решать. PRIMARY KEY
  `(user_id, game_id)` гарантирует, что у пользователя ровно
  одна оценка на игру.

#### `get_user_rating(user_id, game_id)`
- **SQL:** `SELECT score FROM ratings WHERE user_id=%s AND game_id=%s`.
- **Возвращает:** `int` или `None`. Используется для подсветки
  текущей оценки в `game.html`.

#### `get_user_ratings(user_id)`
- **SQL:** `JOIN ratings + games WHERE user_id=%s
  ORDER BY score DESC, title` — все оценённые игры для профиля.

#### `get_user_stats(user_id)`
- **SQL:** `COUNT(*) AS games_rated,
  ROUND(AVG(score), 1) AS avg_score_given FROM ratings WHERE user_id=%s`.
- **Возвращает:** словарь со статистикой; если оценок нет —
  `games_rated=0`, `avg_score_given=NULL`.

### 3.3 Рекомендации и похожие игры

#### `get_similar_games(game_id, limit=4)`
- **SQL:** игры, у которых есть теги исходной игры, исключая её саму,
  с `COUNT(*) AS shared_tags`, отсортировано по числу общих тегов.
- **Ключевой приём:** подзапрос `tag_id IN (SELECT tag_id FROM
  game_tags WHERE game_id = %s)` достаёт «теги исходной игры»;
  верхний `JOIN` находит все игры, у которых хотя бы один такой тег;
  `GROUP BY + COUNT(*)` считает пересечение.

#### `get_global_top(limit=4, exclude_user_id=None)`
- **Назначение:** игры с лучшей средней оценкой среди всех.
  Используется для гостей и как fallback в рекомендациях.
- **SQL:** агрегат `AVG(score)` и `COUNT(score)`, `ORDER BY
  avg_score DESC, ratings_count DESC`. При наличии `exclude_user_id`
  отсекает уже оценённые этим пользователем игры через
  `NOT EXISTS`.
- **Ключевой приём:** именованные параметры
  (`%(uid)s`, `%(limit)s`) — можно повторно подставлять один
  параметр в нескольких местах. И `::int IS NULL` — без явного
  каста PostgreSQL не понимает тип NULL-параметра.

#### `get_recommendations(user_id, limit=4)`
**Самая интересная функция проекта.** Алгоритм:

1. Сначала отдельным SELECT-ом считаем число оценок пользователя.
2. Если `cnt < 3` — **холодный старт**: вернуть глобальный топ
   без уже оценённых игр, проставив `source='global'`.
3. Иначе — **CTE-запрос с тремя CTE**: taste / candidates / scored
   (подробно разобран в разделе 2, пример 2.2).
4. Если персональных получилось меньше `limit` — **padding**:
   дополнить глобальным топом, исключая (а) уже оценённые игры
   (на стороне БД через `exclude_user_id`) и (б) уже показанные
   персональные (в Python через `set` `shown_ids`).
5. Каждой строке проставить поле `source = 'personal' | 'global'`.

**Ключевой приём:** CTE — это «временные именованные подзапросы»
прямо внутри одного SELECT-а. Они делают сложный запрос читаемым,
как пайплайн шагов: «сначала посчитай вкус, потом возьми
кандидатов, потом скоринг — и наконец отбери лучших».

### 3.4 Загрузка игры для редактирования

#### `get_game_for_edit(game_id)`
- **Назначение:** загружает все редактируемые поля + списки
  текущих id для предотметки чекбоксов.
- **SQL:** четыре простых запроса в одном курсоре —
  `SELECT … FROM games WHERE game_id=%s`, затем `SELECT genre_id
  FROM game_genres WHERE game_id=%s` (и аналогично для тегов и
  платформ).
- **Возвращает:** словарь `{game_id, title, release_date, description,
  developer_id, publisher_id, genre_ids:[…], tag_ids:[…],
  platform_ids:[…]}` или `None`.

### 3.5 Транзакционные операции

#### `create_game(title, release_date, description, developer_id,
new_developer_name, publisher_id, new_publisher_name, genre_ids,
tag_ids, platform_ids, new_genre_names, new_tag_names, new_platform_names)`

**Главный пример ACID-атомарности в проекте.** Вся работа по
созданию игры выполняется как **одна транзакция**:

```python
with get_connection() as conn:
    with conn.cursor() as cur:
        # a) Разрешить разработчика
        if new_developer_name:
            INSERT INTO developers (name) VALUES (%s) RETURNING developer_id
            → перезаписываем developer_id

        # a) Разрешить издателя
        if new_publisher_name:
            INSERT INTO publishers (name) VALUES (%s) RETURNING publisher_id
            → перезаписываем publisher_id

        # c) Вставить саму игру
        INSERT INTO games (...) VALUES (...) RETURNING game_id

        # b) find-or-create жанры
        for name in new_genre_names:
            INSERT INTO genres (name) VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING genre_id
            → добавляем id в all_genre_ids

        # b) аналогично теги и платформы

        # d) Связи (через set — дедупликация)
        for gid in set(all_genre_ids):
            INSERT INTO game_genres (game_id, genre_id) VALUES (%s, %s)
        # … game_tags, game_platforms

    # e) Выход из конкретного `with conn:` без исключения →
    #    psycopg 3 автоматически делает COMMIT.
    #    Если на любом шаге было исключение → автоматический ROLLBACK.
    return game_id
```

**Ключевые приёмы:**

- **Транзакция = атомарность.** Если на шаге `c` (вставка игры)
  всё ок, а на шаге `d` падает БД (например, кончилась
  последовательность) — `with conn:` вызовет ROLLBACK, и в БД
  не останется ни новой игры, ни новых жанров/тегов. Никаких
  «полу-созданных» игр.
- **find-or-create через `ON CONFLICT DO UPDATE … RETURNING`.**
  Хитрость: чтобы получить `RETURNING id` и для «вставил», и для
  «уже было», нельзя написать `DO NOTHING` (он не возвращает
  строку, если конфликт). Поэтому делается «фиктивный апдейт»
  `SET name = EXCLUDED.name` — он не меняет ничего по сути, но
  гарантирует, что `RETURNING` вернёт `id` в обоих случаях.
- **Дедупликация через `set()`** — если пользователь и отметил
  чекбокс «open-world», и вписал в «новые теги» тоже «open-world»,
  то после find-or-create оба id будут одинаковыми; `set` сворачивает
  их в один, и `INSERT INTO game_tags` не упадёт на PRIMARY KEY.
- **Приоритет «новое над выбранным».** Если заполнено
  `new_developer_name`, оно переопределяет `developer_id`. Это
  явное правило — текстовое поле сильнее селекта.

#### `update_game(game_id, … те же параметры)`

**Та же транзакция, но для редактирования.** Отличия от
`create_game`:

1. Шаг `c` заменён на `UPDATE games SET title=%s, release_date=%s,
   description=%s, developer_id=%s, publisher_id=%s WHERE game_id=%s`.
2. Шаг `d` — **«удалить и вставить заново»**:
   ```sql
   DELETE FROM game_genres    WHERE game_id = %s;
   DELETE FROM game_tags      WHERE game_id = %s;
   DELETE FROM game_platforms WHERE game_id = %s;
   -- затем INSERT каждого выбранного id
   ```

**Ключевой приём «удалить и вставить заново».** Связи многие-ко-
многим — это «галочки»: либо есть, либо нет. Чтобы согласовать
текущее состояние с пользовательским выбором, проще всего
удалить всё старое и записать всё новое. Не нужно сравнивать
по одному; код одинаково корректен и для добавления, и для
снятия галочки, и для замены целиком.

Атомарность та же: всё внутри одной транзакции. Если на каком-то
шаге упадём — старые связи остаются на месте (rollback откатит
DELETE-ы тоже).

#### `_clean_names(names)` (вспомогательная)
- Убирает пробелы, пустые элементы, дубликаты, сохраняет порядок
  первого появления. Используется в `create_game` и `update_game`
  для чистки списков «новых» имён до `INSERT … ON CONFLICT`.

---

## 4. РАЗБОР `app.py`

Все маршруты опираются на три «глобальных» механизма:

- **`@app.before_request def check_csrf()`** — для POST/PUT/PATCH/DELETE
  сверяет `session["csrf_token"]` и `request.form["csrf_token"]`
  через `hmac.compare_digest` (постоянное время). При несовпадении —
  `abort(400)`.
- **`@app.context_processor inject_user()`** — кладёт `current_user`
  во все шаблоны: `db.get_user_by_id(session["user_id"])` или `None`.
- **`@app.context_processor inject_csrf()`** — кладёт `csrf_token`
  во все шаблоны.

И декоратор `admin_required`:
- не залогинен → flash + `redirect(url_for("login"))`;
- залогинен, но `is_admin=False` → `abort(403)`.

### Маршруты

| Маршрут | Метод | Что делает | Какую `db.py`-функцию вызывает | Защита |
|---|---|---|---|---|
| `/` | GET | Каталог + фильтры + рекомендации. Читает `genre_id` и `tag_id` через `safe_int`; если оба None — `get_all_games`, иначе `get_games_filtered`. Рекомендации: залогинен — `get_recommendations`, гость — `get_global_top` + `source='global'`. | `get_all_games`, `get_games_filtered`, `get_all_genres`, `get_all_tags`, `get_recommendations`, `get_global_top` | публичный |
| `/game/<int:game_id>` | GET | Карточка игры (см. раздел 2.1). | `get_game_by_id`, `get_user_rating`, `get_similar_games` | публичный; `is_admin` определяет показ кнопки «Редактировать» в шаблоне |
| `/search` | GET | Поиск по названию. Сначала `validate_search_query`, потом `search_games`. Пустая строка — пустой список. | `search_games` | публичный |
| `/rate/<int:game_id>` | POST | Поставить/изменить оценку. Если не залогинен — flash + redirect на `/login`. Валидирует `score` через `validate_score`, затем `set_rating`. Возвращается на ту же карточку. | `set_rating` | требует входа; CSRF (через `before_request`) |
| `/profile` | GET | Профиль текущего пользователя: статистика + список оценённых игр. Без входа — flash + redirect. | `get_user_ratings`, `get_user_stats` | требует входа |
| `/register` | GET, POST | GET — форма. POST — валидируем `username/email/password`, хэшируем `generate_password_hash`, `create_user`, кладём `user_id` в сессию. Ловим `UniqueViolation` (дубликат). Если уже залогинен — сразу на `/`. | `create_user` | публичный; CSRF на POST |
| `/login` | GET, POST | GET — форма. POST — `get_user_by_username` + `check_password_hash`. Ошибка обобщённая «неверный логин или пароль». При успехе — `session["user_id"]`. Если уже залогинен — сразу на `/`. | `get_user_by_username` | публичный; CSRF на POST |
| `/logout` | POST | `session.clear()` + flash + redirect на `/`. | — | CSRF на POST (в `base.html` кнопка «Выход» — мини-форма со скрытым `csrf_token`) |
| `/admin/add_game` | GET, POST | GET — рендер формы (получаем все справочники). POST — собираем поля, валидируем `validate_game_title` + опционально `validate_release_date`, гоняем списки через `safe_int` и `parse_new_names`, зовём `create_game`. Успех → flash + redirect на `/game/<new_id>`. Ошибка — flash + повторный рендер формы. | `get_all_developers`, `get_all_publishers`, `get_all_genres`, `get_all_tags`, `get_all_platforms`, `create_game` | `@admin_required` + CSRF на POST |
| `/admin/edit_game/<int:game_id>` | GET, POST | GET — `get_game_for_edit` + справочники, форма с предзаполненными значениями. POST — те же шаги валидации + `update_game`. Если игра не найдена — flash + redirect на `/`. | `get_game_for_edit`, `get_all_*` справочники, `update_game` | `@admin_required` + CSRF на POST |

---

## 5. ШАБЛОНЫ

`templates/` использует наследование Jinja2: `base.html` — основа,
остальные расширяют его через `{% extends "base.html" %}` и
переопределяют блоки `title` и `content`.

| Шаблон | Где используется | Что делает |
|---|---|---|
| `base.html` | базовый | Шапка с навигацией (логотип, ссылки на логин/регистрацию или на профиль/выход; для админа дополнительно «🛠 Добавить игру»). Форма выхода — мини-POST с `csrf_token`. Контейнер для флэш-сообщений и `{% block content %}`. Подвал. |
| `index.html` | `/` (`index`) | Заголовок «Каталог игр». Блок рекомендаций (подпись зависит от `source`). Форма поиска (GET). Форма фильтров (GET): два `<select>` + кнопка + кнопка сброса. Сетка карточек игр. Сообщения «ничего не найдено» / «игр пока нет». |
| `game.html` | `/game/<id>` (`game_detail`) | Карточка игры — см. раздел 2.1. Ссылка «✏️ Редактировать» видна только если `current_user.is_admin`. Форма оценки видна только залогиненным. |
| `search.html` | `/search` (`search`) | Заголовок «🔍 Поиск игр», форма с autofocus, информация о числе результатов со склонением, сетка карточек или «ничего не найдено». |
| `profile.html` | `/profile` (`profile`) | Шапка профиля (аватар, имя, дата регистрации), плитка статистики, список оценок одной колонкой. Использует `current_user` напрямую. |
| `register.html` | `/register` GET | Поля username/email/password с HTML-валидацией, скрытый `csrf_token`. Отображает `error`, если рендер пришёл после неудачного POST. |
| `login.html` | `/login` GET | username/password + `csrf_token`. Отображает обобщённую ошибку. |
| `admin_add_game.html` | `/admin/add_game` GET (и при ошибке POST) | Большая форма из 6 секций: основное, разработчик (select + текст), издатель (select + текст), жанры (чекбоксы + новые через запятую), теги (то же), платформы (то же). Скрытый `csrf_token`. Кнопки «💾 Сохранить» / «Отмена». |
| `admin_edit_game.html` | `/admin/edit_game/<id>` GET (и при ошибке POST) | Та же структура, что и `admin_add_game.html`, но **предзаполненная**: `value="{{ game.title }}"`, `value="{{ game.release_date.isoformat() if game.release_date else '' }}"`, `selected` в select-ах (`{% if dev.developer_id == game.developer_id %}`), `checked` в чекбоксах (`{% if genre.genre_id in game.genre_ids %}` и аналогично для тегов/платформ). Ссылка «← Вернуться к карточке игры». |

---

## 6. БЕЗОПАСНОСТЬ В КОДЕ

Конкретные места, на которые можно показать пальцем на защите.

### 6.1 Параметризованные запросы (защита от SQL-инъекций)
Везде в `db.py`. Несколько примеров:
- `db.py:147` — `cur.execute(sql, (f"%{query}%",))` — поисковая
  строка **никогда** не склеивается в SQL, она передаётся
  отдельным параметром, psycopg её экранирует.
- `db.py:163-166` — `INSERT INTO users (…) VALUES (%s,%s,%s)`.
- `db.py:343` — `cur.execute(sql, (genre_id, tag_id, genre_id, tag_id))`
  для фильтров.
- `db.py:407` — именованные параметры `{"uid": …, "limit": …}`.

### 6.2 Хэширование паролей
- `app.py:8` — `from werkzeug.security import generate_password_hash, check_password_hash`.
- `app.py:214` — при регистрации: `password_hash = generate_password_hash(password)`
  и затем `db.create_user(username, email, password_hash)`. В БД
  попадает только хэш.
- `app.py:241` — при логине: `check_password_hash(user["password_hash"], password)`.
- `db.py` нигде не возвращает `password_hash` наружу, кроме
  `get_user_by_username` (нужен для проверки).

### 6.3 CSRF
- Генерация токена: `app.py:35-39` — `get_csrf_token()` создаёт
  `secrets.token_hex(32)` и кладёт в `session["csrf_token"]`.
- Прокидывание во все шаблоны: `app.py:67-70` — context_processor
  `inject_csrf`.
- Проверка в каждом мутирующем запросе: `app.py:42-53`:
  ```python
  if request.method in ("POST", "PUT", "PATCH", "DELETE"):
      session_token = session.get("csrf_token", "")
      form_token    = request.form.get("csrf_token", "")
      if not session_token or not hmac.compare_digest(session_token, form_token):
          abort(400)
  ```
  `hmac.compare_digest` — сравнение **постоянного времени**, защита
  от timing-атак.
- В каждой POST-форме есть `<input type="hidden" name="csrf_token"
  value="{{ csrf_token }}">`: см. `register.html:14`, `login.html:14`,
  `game.html:92` (форма оценки), `base.html:22` (форма выхода),
  `admin_add_game.html:9`, `admin_edit_game.html:16`.

### 6.4 Роль `gamedb_app` (least privilege)
- `db.py:9-17` — `get_connection()` использует `DB_USER` из `.env`,
  по факту это `gamedb_app` (см. PROJECT_LOG, сессия 7).
- У роли есть только `SELECT / INSERT / UPDATE / DELETE` на нужных
  таблицах + `USAGE, SELECT` на последовательностях. Нет
  `SUPERUSER`, `CREATE`, `DROP`, `ALTER`, `TRUNCATE`. Если бы
  кто-то сумел всё-таки внедриться через SQL — он не сможет
  поломать схему. Учётка `postgres` используется только для DDL/
  миграций.

### 6.5 Валидация ввода (validators.py)
- `validate_username` — длина, регулярка `^[a-zA-Z0-9_-]+$`.
- `validate_email` — длина + регулярка с `@` и доменом.
- `validate_password` — длина ≥ 8.
- `validate_score` — целое в [1, 10] (плюс на стороне БД
  `CHECK (score BETWEEN 1 AND 10)`).
- `validate_search_query` — длина ≤ 200.
- `validate_game_title` — непустая, ≤ 300 (совпадает со схемой
  `VARCHAR(300)`).
- `validate_release_date` — `datetime.date.fromisoformat` строго
  YYYY-MM-DD.
- `parse_new_names` — разбивает по запятой, чистит пробелы,
  убирает дубликаты с регистронезависимым сравнением.
- `safe_int(value, min_val=1)` — критично для id-параметров из
  URL. Возвращает `int ≥ 1` или `None`; никакой склейки строк
  с пользовательским вводом не происходит (`app.py:98-99`,
  `298-310` и т.д.).

### 6.6 Сессионные куки
- `app.py:23` — `app.secret_key` берётся из `.env` (`SECRET_KEY =
  secrets.token_hex(32)`).
- `app.py:26-30` — `SESSION_COOKIE_HTTPONLY=True`,
  `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE` —
  включается флагом из `.env` (в проде включён, локально выключен,
  иначе по HTTP куки не работают).

### 6.7 Обобщённое сообщение об ошибке логина
- `app.py:241-242` — «Неверный логин или пароль.» — не раскрывает,
  что именно неверно. Это защита от перебора username-ов
  (timing/contents-side-channel).

### 6.8 Контроль доступа админских маршрутов
- `app.py:75-91` — `admin_required` (см. выше).
- Применяется к `admin_add_game` (`app.py:263`) и `admin_edit_game`
  (`app.py:357`).
- Гость → flash + redirect на `/login`. Не-админ → `abort(403)`.

---

## 7. КЛЮЧЕВЫЕ РЕШЕНИЯ И «ПОЧЕМУ»

Раздел для устных ответов.

### Почему чистый SQL без ORM?
Это учебный проект **по курсу «Базы данных»**. ORM (SQLAlchemy и т.п.)
прячет SQL — а нам нужно его показывать и объяснять. На голом
psycopg 3 видно каждый JOIN, каждый CTE, каждое `ON CONFLICT`.
Преподаватель может ткнуть пальцем в любой запрос и спросить,
что он делает, — и ответ будет про SQL, а не про настройки модели.

### Почему весь SQL в `db.py`, а не в маршрутах?
Это разделение слоёв. Маршрут (`app.py`) занимается HTTP: читает
форму, валидирует, выбирает шаблон. БД (`db.py`) занимается данными.
Если завтра захочется добавить второй интерфейс (например, JSON-API),
достаточно будет вызвать те же функции из `db.py`. Также удобно
для рецензента: «где у тебя SQL?» — открываешь один файл.

### Почему серверный рендеринг (Jinja2), без отдельного фронтенда?
Минимальная связка: один Python-процесс, один HTML-ответ. Не нужно
объяснять SPA, состояние клиента, CORS. Защищать проект про БД
гораздо проще, когда фокус остаётся на БД и SQL, а UI — это
шаблоны.

### Почему создание и редактирование игры обёрнуто в транзакцию?
Это **главный пример ACID-атомарности** в проекте. Создание
игры — это много шагов: вставить разработчика, вставить издателя,
вставить запись игры, найти-или-создать жанры/теги/платформы,
вставить N связей. Если упасть посередине без транзакции — в БД
останется полу-игра без связей или новые жанры, привязанные
к несуществующей игре. С `with conn:` либо проходит весь набор
изменений, либо ни одного. То же для редактирования: «удалить
и вставить заново» внутри транзакции — это безопасная атомарная
операция «согласовать связи», а не «опасная DELETE без вставки».

### Почему `find-or-create` через `ON CONFLICT DO UPDATE SET name=EXCLUDED.name RETURNING id`?
Хочется одной командой: «дай мне id; если такого имени ещё нет —
создай». `INSERT … ON CONFLICT DO NOTHING RETURNING id` **не
возвращает строку, если конфликт**. Поэтому делается «фиктивное
обновление» — оно перезаписывает имя на то же самое значение,
но даёт `RETURNING id`. Один запрос вместо паттерна
«SELECT, потом INSERT если не нашли» — короче и без гонок.

### Почему «удалить и вставить заново» для связей игры?
Связи многие-ко-многим — это набор галочек. Чтобы привести
старый набор к новому, можно (а) делать diff и точечные
INSERT/DELETE — много кода, легко ошибиться; или (б)
просто DELETE всё, INSERT всё — три строки, одинаково
корректно. Внутри транзакции это безопасно.

### Почему CSRF реализован вручную, а не через Flask-WTF?
Учебный проект, держим зависимости минимальными. Хватает 15 строк:
`secrets.token_hex(32)` в сессии + `hmac.compare_digest` в
`before_request`. Бонус — становится видно, что такое CSRF на
уровне механики, а не «магическое декорирование от библиотеки».

### Почему `safe_int` и параметризованные `WHERE …::int IS NULL`?
Все id из URL приводятся к `int ≥ 1` или `None`. Никакого `f"…{id}…"`
в SQL. Каст `%s::int IS NULL` нужен потому, что PostgreSQL не может
вывести тип у голого NULL-параметра, если он не привязан к колонке;
без каста запрос падает с `IndeterminateDatatype` (был такой баг
с фильтром «жанр + Все теги», лог упоминает коммит `e9b0565`).

### Почему `gamedb_app`, а не `postgres`?
Принцип **least privilege**. Если кто-то всё-таки прорвётся через
SQL-инъекцию (даже несмотря на параметризацию), у него на руках
будет роль, которая не умеет `DROP TABLE`, `ALTER`, `TRUNCATE`.
Учётка `postgres` — только для DDL и миграций, и её пароль не
попадает в `.env` приложения.

### Почему recommendations — это CTE, а не один большой SELECT?
Запрос делает три логически разных шага: «посчитай вкус», «найди
кандидатов», «оцени их». CTE превращает это в читаемый пайплайн.
Если бы это был один большой запрос с подзапросами — было бы
сложнее объяснять и поддерживать. На защите CTE прекрасно
ложатся в три предложения.

---

## 8. ЗАМЕЧЕННОЕ ПРИ ЧТЕНИИ

Это наблюдения по реальному коду — ничего не править, просто
сообщить автору на случай, если он захочет учесть.

1. **Дубликаты в справочниках dev/pub возможны.** У `developers`
   и `publishers` поле `name` — `NOT NULL` без `UNIQUE`
   (см. `schema.sql:11-19`). В `create_game` / `update_game`
   ветка «новый разработчик» делает голый `INSERT INTO developers
   (name) VALUES (%s) RETURNING developer_id` без `ON CONFLICT`
   (см. `db.py:568-573` и `db.py:716-722`). Это **не баг**, а
   принятое решение (повторяющиеся имена разных студий разрешены),
   но стоит знать, что повторный ввод «CD Projekt Red» создаст
   вторую запись.

2. **`get_game_by_id` оборачивает только `store_links` в
   `try/except`.** Если по какой-то причине `game_store_links`
   нет (старая БД, не применена миграция Phase 2), функция
   честно вернёт пустой список. Для остальных запросов такой
   защиты нет — это намеренно, они опираются на актуальную схему.

3. **При ошибке POST на `/admin/add_game` форма теряет введённые
   значения.** В `app.py:319-324` и `app.py:346-351` повторный
   рендер `admin_add_game.html` не передаёт обратно `title`,
   `release_date`, выбранные `genre_ids` и т.д. Пользователю
   придётся вписать всё заново. То же поведение и в
   `admin_edit_game` (там предзаполнение идёт от исходного `game`,
   а не от того, что он редактировал).

4. **`@app.context_processor inject_csrf` вызывает `get_csrf_token()`
   на каждый запрос.** Это означает, что даже на чистый GET
   рендер шаблона создаёт сессию с CSRF-токеном. Это нормально и
   нужно для последующих форм, но стоит знать, что сессионная кука
   ставится посетителю сразу.

5. **`avg_score` в шаблонах появляется как `Decimal` от
   `ROUND(AVG(…), 1)`.** В Jinja2 он печатается нормально
   (`{{ game.avg_score }}` → «8.5»), но при сравнении с
   плавающей точкой это `Decimal`. На отображение не влияет;
   написано, чтобы помнить тип.

6. **`store_links` берёт «как есть» поле `url`.** В шаблоне
   `game.html:121` ссылка `target="_blank" rel="noopener noreferrer"`
   — хорошо. URL приходит из seed-ов (статичные данные), пользователи
   их не вводят. Если в будущем появится форма добавления магазинов,
   потребуется отдельная валидация URL.

7. **`new_genre_names`/`new_tag_names`/`new_platform_names` дважды
   обрабатываются.** `parse_new_names` чистит и дедуплицирует на
   уровне `app.py`, а потом `_clean_names` ещё раз чистит уже
   внутри `create_game`/`update_game`. Это не баг — двойной
   страховочный пояс, но строго говоря избыточно (второй вызов
   почти всегда ничего не меняет).

8. **`seed.sql` и `seed_delta.sql` пересекаются.** `seed.sql`
   рассчитан на чистую БД и **не** использует `ON CONFLICT` для
   игр; `seed_delta.sql` рассчитан на существующую БД с одной
   Dishonored и аккуратно добавляет остальное. Применять их
   одновременно нельзя — нужно выбрать сценарий. В PROJECT_LOG
   это явно прописано, в самих файлах — комментариями в шапке.

