# DB_FUNCTIONS_DEEP_DIVE — глубокий разбор сложных мест проекта

> Этот файл — «шпаргалка для защиты». Здесь собрано всё, что разбиралось
> подробно: как читать SQL-плейсхолдеры, где живут ограничения БД, и построчный
> разбор самых сложных функций `db.py` (фильтры, рекомендации, админка), а также
> пара важных вопросов по `app.py` (контроль доступа, GET/POST, `current_user`).
>
> Всё строго по фактическому коду. Документ ничего не меняет в проекте.

## Содержание

1. [Основы SQL в этом проекте: `%s`, wildcard `%…%`, `VALUES`, `UNIQUE`](#1-основы-sql)
2. [Три вопроса по `app.py`: `abort(403)`, GET/POST, откуда `current_user`](#2-три-вопроса-по-apppy)
3. [`get_games_filtered` — каталог с фильтрами](#3-get_games_filtered)
4. [`get_similar_games` — похожие игры по тегам](#4-get_similar_games)
5. [`get_global_top` — глобальный топ по оценке](#5-get_global_top)
6. [`get_recommendations` — персональные рекомендации](#6-get_recommendations)
7. [Админка: транзакции, `get_game_for_edit`, `create_game`, `update_game`](#7-админка-транзакции)

---

## 1. Основы SQL

### `%s` — это плейсхолдер psycopg, а НЕ часть SQL

`%s` — метка драйвера psycopg, означающая «сюда я потом подставлю значение».
Сам PostgreSQL никаких `%s` не видит. Механика двухшаговая: пишем запрос с
дырками и отдельно — значения для них.

```python
cur.execute("... WHERE user_id = %s", (5,))
#                              ↑ дырка    ↑ чем заполнить
```

psycopg берёт `5`, **безопасно экранирует** и подставляет → `... WHERE user_id = 5`.

**Зачем так, а не склейка строк.** Если бы писали `f"... WHERE name = '{name}'"`,
злоумышленник мог бы ввести `'; DROP TABLE users; --` и сломать БД — это
**SQL-инъекция**. Через `%s` пользовательский текст всегда попадает как
**данные**, а не как часть команды. Правило проекта: значения — только через `%s`.

> Буква `s` — от строкового формата Python, но подставлять можно любой тип:
> число, строку, дату, `None`. «`s`» не значит «только строка».

### `%…%` внутри значения — это уже wildcard языка SQL (LIKE/ILIKE)

Когда `%` стоит **внутри самого значения** (как в `f"%{query}%"`, `db.py:146`) —
это знак самого SQL, шаблонный символ (wildcard) для оператора `ILIKE`. В `ILIKE`
символ `%` означает «здесь может быть любой текст любой длины».

| Шаблон | Что находит |
|--------|-------------|
| `'ведьмак'` | строго «ведьмак» |
| `'ведьмак%'` | начинается с «ведьмак» |
| `'%ведьмак'` | заканчивается на «ведьмак» |
| `'%ведьмак%'` | **содержит** «ведьмак» где угодно |

Поэтому `search_games` делает `f"%{query}%"` — ищет **по подстроке**: ввёл
«ведь» → нашлось «Ведьмак 3».

**Это не противоречит пункту про `%s`.** Смотри `db.py:146`:

```python
cur.execute(sql, (f"%{query}%",))
```
- в `sql` стоит `... WHERE g.title ILIKE %s` — тут `%s` это **плейсхолдер**;
- значением передаём строку `"%ведь%"` — и в **ней** символы `%` это **wildcard
  для ILIKE**. Сам текст пользователя по-прежнему идёт как данные, не вклеивается.

### `VALUES (%s, %s, %s)` — три плейсхолдера для трёх колонок

```sql
INSERT INTO users (username, email, password_hash)
VALUES            (%s,       %s,    %s)
```
Читается по парам: `username` ← 1-е значение, `email` ← 2-е, `password_hash` ← 3-е.
Значения передаём кортежем в том же порядке (`db.py:165`):

```python
cur.execute(sql, (username, email, password_hash))
```

Три дырки = три значения. **Порядок важен**: перепутаешь — email уедет в
username.

### Где `UNIQUE`? В `schema.sql`, не в `db.py`

В `db.py` слова `UNIQUE` нет, и быть не должно. Разделение:
- **`db.py`** — DML (Data Manipulation Language): команды, что читают и меняют
  *данные* — `SELECT`, `INSERT`, `UPDATE`, `DELETE`.
- **`schema.sql`** — DDL (Data Definition Language): команды, что описывают
  *структуру* — `CREATE TABLE` и ограничения `UNIQUE`, `PRIMARY KEY`, `CHECK`,
  `NOT NULL`.

`UNIQUE` встроен в таблицу один раз при создании (`schema.sql:89-90`):

```sql
CREATE TABLE users (
    user_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50)  NOT NULL UNIQUE,   -- ← тут
    email    VARCHAR(255) NOT NULL UNIQUE,   -- ← и тут
    ...
);
```

PostgreSQL **физически не позволит** двум строкам иметь одинаковый `username`
или `email`. При `INSERT` с занятым именем БД сама откажет и вернёт ошибку;
psycopg превратит её в `psycopg.errors.UniqueViolation`, которую ловит
`register` (`app.py:219`).

**Почему это надёжнее проверки в Python.** Проверка «есть ли уже такой email?»
в коде имеет дыру: между «проверил — нет» и «вставил» другой запрос мог успеть
вставить такой же email (состояние гонки). Ограничение `UNIQUE` в БД — последний
абсолютный барьер.

> Тот же принцип в других местах схемы: `CHECK (score BETWEEN 1 AND 10)`
> (`schema.sql:104`) — не пустит оценку вне 1–10; `PRIMARY KEY (user_id, game_id)`
> в `ratings` (`schema.sql:106`) — не пустит две оценки одной игры от одного
> пользователя; `name … UNIQUE` у жанров/тегов/платформ (`schema.sql:24,29,34`) —
> на нём срабатывает `ON CONFLICT (name)` в find-or-create.

---

## 2. Три вопроса по `app.py`

### Почему `abort(403)` в `admin_required` (`app.py:89`)

`403 Forbidden` = «я знаю, кто ты, но тебе сюда нельзя». В `admin_required` два
случая отказа:
- **Гость** (не залогинен) → личность неизвестна, ему `flash + redirect на
  /login` (предложить войти);
- **Залогинен, но `is_admin = False`** → личность известна, вход не поможет
  (он уже вошёл), не хватает прав → `abort(403)`.

Если бы не-админа тоже слали на `/login`, был бы замкнутый круг: вошёл → снова
на логин → вошёл… Redirect на login = «не аутентифицирован», `403` =
«аутентифицирован, но не авторизован».

### Откуда Flask знает, GET это или POST

`db.py` тут ни при чём (он про данные). Метод определяется в `app.py`:
- в самом HTTP-запросе первая строка содержит метод (`GET /search`,
  `POST /rate/3`);
- в `@app.route(...)` перечисляем разрешённые методы:
  - `@app.route("/search")` — по умолчанию только GET;
  - `@app.route("/rate/<int:game_id>", methods=["POST"])` — только POST;
  - `@app.route("/register", methods=["GET", "POST"])` — оба.

Если маршрут принимает оба, внутри ветвимся: `if request.method == "POST":`
(`app.py:203` в `register`). Один путь `/register`: GET рисует форму, POST
принимает данные.

### Откуда берётся `current_user` в шаблонах

Это **не** встроенная переменная Flask. Её создаёт наш `inject_user`
(`app.py:58-64`):

```python
@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = db.get_user_by_id(user_id)
        return {"current_user": user}
    return {"current_user": None}
```

- Ключ словаря `"current_user"` — это и есть **имя переменной** в шаблоне.
- `@app.context_processor` — декоратор, который говорит Flask: «перед рендером
  **любого** шаблона вызови эту функцию и подмешай возвращённый словарь в
  переменные шаблона». Поэтому `current_user` доступен везде без ручной передачи
  через `render_template(...)`.
- Внутри лежит результат `db.get_user_by_id(user_id)` (`db.py:184`), а его SQL
  возвращает колонку `is_admin` (`db.py:189`). Поэтому `current_user.is_admin` —
  обращение к полю этого словаря.
- `user_id` — из сессии, куда его положили при входе (`app.py:244`) или
  регистрации (`app.py:216`). У гостя сессии нет → `current_user = None`.

Полная цепочка:

```
вход → session["user_id"] = 5
   ↓ (на каждый запрос)
inject_user(): user_id=5 → db.get_user_by_id(5) → {... "is_admin": True ...}
   ↓ возвращает {"current_user": <словарь>}
@app.context_processor подмешивает во ВСЕ шаблоны
   ↓
base.html: {% if current_user.is_admin %}  →  рисуем кнопку
```

Отрисовка кнопок (`base.html:15`, `game.html:13`) — косметика по `is_admin`.
Реальная защита маршрута — `admin_required` на сервере: даже если подделать HTML
и нарисовать кнопку, на сервере остановит `abort(403)`.

---

## 3. `get_games_filtered`

Каталог с фильтром (`db.py:317-344`). Зовётся из `index()` только когда задан
хотя бы один фильтр; иначе там `get_all_games()`. Цель — **одним запросом**
обслужить все комбинации (жанр / тег / оба / ничего).

```python
SELECT DISTINCT
    g.game_id, g.title, g.release_date, g.description,
    d.name AS developer, p.name AS publisher
FROM games g
LEFT JOIN developers d USING (developer_id)
LEFT JOIN publishers  p USING (publisher_id)
LEFT JOIN game_genres gg ON g.game_id = gg.game_id AND gg.genre_id = %s
LEFT JOIN game_tags   gt ON g.game_id = gt.game_id AND gt.tag_id   = %s
WHERE (%s::int IS NULL OR gg.genre_id IS NOT NULL)
  AND (%s::int IS NULL OR gt.tag_id   IS NOT NULL)
ORDER BY g.title
```

### Два вида JOIN

- `LEFT JOIN developers` / `LEFT JOIN publishers` — **справочные**, просто
  достать имена. `LEFT`, чтобы игра показалась даже без указанного dev/pub.
- `LEFT JOIN game_genres gg ON g.game_id = gg.game_id AND gg.genre_id = %s` —
  **фильтрующий**, главный трюк. Условие `gg.genre_id = %s` стоит **внутри `ON`**
  (условие склейки), а не в `WHERE`:
  - если у игры есть искомый жанр → строка приклеивается, `gg.genre_id` не `NULL`;
  - если нет → `LEFT JOIN` всё равно оставляет игру, но `gg.*` будут `NULL`.

  Поле `gg.genre_id` становится «лакмусом»: заполнено → жанр есть, `NULL` → нет.

**Почему `ON`, а не `WHERE`.** Условие `gg.genre_id = %s` в `WHERE` сразу
отсеяло бы игры без жанра (их `NULL` не прошёл бы), и `LEFT JOIN` фактически стал
бы `INNER JOIN`. Нам же нужно сохранить все игры до финальной проверки, чтобы тот
же запрос умел «не фильтровать вовсе».

### Трюк в WHERE: «фильтр не задан ИЛИ совпадение есть»

```sql
WHERE (%s::int IS NULL OR gg.genre_id IS NOT NULL)
  AND (%s::int IS NULL OR gt.tag_id   IS NOT NULL)
```
Первая скобка (жанр):
- фильтр не выбран (параметр `NULL`): `%s::int IS NULL` истинно → скобка через
  `OR` истинна → пропускает любую игру (фильтр выключен);
- фильтр выбран (число): `%s::int IS NULL` ложно → остаётся `gg.genre_id IS NOT
  NULL` → проходят только игры, к которым приклеился нужный жанр.

Скобки соединены `AND` → при двух фильтрах игра должна иметь **и** жанр, **и** тег.

`::int` — **явный каст** («считай параметр целым»). У голого `NULL` PostgreSQL не
может вывести тип и падает с `IndeterminateDatatype` — этот баг в проекте чинили.

### Почему параметров четыре: `(genre_id, tag_id, genre_id, tag_id)`

| № `%s` | Где в SQL | Значение |
|--------|-----------|----------|
| 1 | `gg.genre_id = %s` (ON) | `genre_id` |
| 2 | `gt.tag_id = %s` (ON) | `tag_id` |
| 3 | `%s::int IS NULL` (жанр, WHERE) | `genre_id` снова |
| 4 | `%s::int IS NULL` (тег, WHERE) | `tag_id` снова |

Каждый id используется дважды (в `ON` и в `WHERE`), поэтому повторяется в кортеже.
Сравни с `get_global_top`, где **именованные** параметры `%(uid)s` избавляют от
повтора.

### Пример (фильтр: жанр = RPG, тег = dark)

| Игра | Жанры | Теги | `gg.genre_id` | `gt.tag_id` | Проходит? |
|------|-------|------|------|------|-----------|
| Witcher 3 | RPG, … | dark, … | заполнен | заполнен | ✅ |
| Hades | RPG, … | roguelike | заполнен | `NULL` | ❌ (падает на теге) |
| Dishonored | Action, … | dark | `NULL` | заполнен | ❌ (падает на жанре) |

Останется Witcher 3 (и Dark Souls III с такими же метками) — как в проверочном
сценарии №2 из `PROJECT_LOG.md`.

### `DISTINCT`, безопасность

- `SELECT DISTINCT` (убрать одинаковые строки) — здесь «страховочный пояс»: в
  `ON` пришпилен один конкретный id, а пара `(game_id, genre_id)` уникальна
  (PRIMARY KEY, `schema.sql:63`), так что каждая игра и так даёт максимум одну
  строку. Дублей практически не бывает, но `DISTINCT` защищает, если запрос
  усложнят.
- Оба id приходят из URL через `safe_int` (`app.py:98-99`) → гарантированно
  `int ≥ 1` или `None`, и подставляются только через `%s`. Инъекция невозможна.

---

## 4. `get_similar_games`

Похожие игры по тегам, блок на карточке (`db.py:351-376`). Идея: «игры с
наибольшим числом общих тегов».

```python
SELECT
    g.game_id, g.title, g.release_date,
    d.name  AS developer,
    COUNT(*) AS shared_tags
FROM games g
JOIN game_tags  gt ON g.game_id = gt.game_id
LEFT JOIN developers d USING (developer_id)
WHERE gt.tag_id IN (
    SELECT tag_id FROM game_tags WHERE game_id = %s
)
  AND g.game_id != %s
GROUP BY g.game_id, g.title, g.release_date, d.name
ORDER BY shared_tags DESC, g.title
LIMIT %s
```

**Разбор:**
- `FROM games g JOIN game_tags gt` — обычный `JOIN` разворачивает каждую игру в
  **по строке на каждый её тег**.
- `WHERE gt.tag_id IN (SELECT tag_id FROM game_tags WHERE game_id = %s)` — ядро.
  Подзапрос достаёт **теги исходной игры**; `IN (…)` оставляет только строки, чей
  тег входит в этот список. То есть оставляем лишь совпадения с нашей игрой.
- `AND g.game_id != %s` (`!=` — не равно) — исключаем саму игру.
- `GROUP BY … COUNT(*) AS shared_tags` — группируем по игре и считаем, сколько
  строк (= совпавших тегов) у каждой.
- `ORDER BY shared_tags DESC, g.title` — сначала самые похожие.
- `LIMIT %s` — не больше `limit` (по умолчанию 4).

**Параметры:** `(game_id, game_id, limit)`.

**Пример.** Открыли Dishonored с тегами `{dark, stealth, steampunk}`:

| Кандидат | Теги | Совпало | `shared_tags` |
|---|---|---|---|
| Thief | stealth, steampunk, dark | все три | **3** |
| Dark Souls III | dark, hard | dark | **1** |
| Hades | roguelike, fast | — | не попадёт (0 → нет строк) |

> `JOIN game_tags` — обычный (INNER): игра без тегов «похожей по тегам» быть не
> может. `LEFT JOIN developers` — `LEFT`, чтобы показать игру даже без dev.

---

## 5. `get_global_top`

«Лучшее у всех» (`db.py:379-408`). Используется гостям на главной и как
**запасной вариант** в `get_recommendations`.

```python
SELECT
    g.game_id, g.title,
    d.name                 AS developer,
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
LIMIT %(limit)s
```

**Разбор:**
- `JOIN ratings r USING (game_id)` — обычный (INNER), поэтому **игры без оценок в
  топ не попадают** (средней у них нет).
- `ROUND(AVG(r.score), 1)` — средняя оценка, округлённая до 1 знака.
- `COUNT(r.score)` — число оценок.
- `GROUP BY g.game_id, …` — агрегаты считаются по каждой игре.
- `ORDER BY avg_score DESC, ratings_count DESC` — сначала по средней; при равной
  средней выше тот, у кого больше оценок (9.0 от 50 человек > 9.0 от 2).
- `LIMIT %(limit)s`.

**`WHERE` с `exclude_user_id` — «не показывай уже оценённое»** (тот же
выключатель, что в фильтрах):
- `uid` = `NULL` (гость) → `%(uid)s::int IS NULL` истинно → пропускает все игры;
- `uid` задан → `NOT EXISTS (SELECT 1 …)` — «не существует строки, где этот
  пользователь оценил эту игру» → остаются только не оценённые им. `SELECT 1` —
  важен лишь факт наличия строки, не данные.

**Именованные параметры** `%(uid)s`/`%(limit)s` — потому что `uid` встречается
дважды; словарь `{"uid": exclude_user_id, "limit": limit}` (`db.py:407`) избавляет
от повтора.

---

## 6. `get_recommendations`

Персональные рекомендации (`db.py:411-492`) — это **алгоритм из шагов**, не один
запрос.

### Шаг 1. Сколько у пользователя оценок

```python
count_sql = "SELECT COUNT(*) AS cnt FROM ratings WHERE user_id = %s"
```

### Шаг 2. «Холодный старт» — если оценок < 3

```python
if cnt < 3:
    rows = get_global_top(limit, exclude_user_id=user_id)
    return [dict(r, source="global") for r in rows]
```
Угадывать вкус не на чем → глобальный топ (минус уже оценённое), помечаем
`source="global"` (шаблон напишет «Популярное сейчас»). `dict(r, source="global")`
— «возьми строку-словарь и добавь поле source».

### Шаг 3. Персональный запрос с тремя CTE

**CTE** (Common Table Expression) — временные именованные подзапросы через
`WITH имя AS (…)`; читаются как шаги конвейера.

```sql
WITH taste AS (
    SELECT gt.tag_id, AVG(r.score) - 5.5 AS affinity
    FROM ratings r
    JOIN game_tags gt ON gt.game_id = r.game_id
    WHERE r.user_id = %s
    GROUP BY gt.tag_id
),
```
**`taste` — профиль вкуса по тегам.** По каждому тегу оценённых игр считаем
`AVG(r.score) - 5.5`. **Минус 5.5** — это **центрирование**: 5.5 это середина
шкалы 1–10. Выше середины → положительный `affinity` (тег нравится), ниже →
отрицательный. Тег «RPG» со средней 9 → +3.5; «horror» со средней 3 → −2.5.

```sql
candidates AS (
    SELECT g.game_id FROM games g
    WHERE NOT EXISTS (
        SELECT 1 FROM ratings r WHERE r.user_id = %s AND r.game_id = g.game_id
    )
),
```
**`candidates` — игры, которые он ещё не оценивал** (`NOT EXISTS`). Рекомендовать
оценённое незачем.

```sql
scored AS (
    SELECT c.game_id, SUM(t.affinity) AS rec_score
    FROM candidates c
    JOIN game_tags gt ON gt.game_id = c.game_id
    JOIN taste     t  ON t.tag_id   = gt.tag_id
    GROUP BY c.game_id
)
```
**`scored` — оценка кандидатов.** Для каждого берём его теги (`JOIN game_tags`),
к каждому тегу подтягиваем `affinity` из `taste` (`JOIN taste`) и `SUM` складываем.
Больше «любимых» тегов → выше `rec_score`; нелюбимые (отрицательные) уменьшают.

> Тонкость: `JOIN taste` — обычный (INNER). В сумму попадают **только теги,
> которые пользователь уже встречал** (только они есть в `taste`). Кандидат без
> единого «знакомого» тега не получит строки в `scored` и в рекомендации не
> попадёт.

```sql
SELECT g.game_id, g.title, d.name AS developer, s.rec_score
FROM scored s
JOIN games g ON g.game_id = s.game_id
LEFT JOIN developers d USING (developer_id)
ORDER BY s.rec_score DESC
LIMIT %s
```
Приклеиваем название и разработчика, сортируем по `rec_score DESC`, берём `limit`.
В Python ставим `source="personal"` (`db.py:474`).

### Шаг 4. Дополнение (padding), если личных не хватило

```python
if len(personal) >= limit:
    return personal
shown_ids = {r["game_id"] for r in personal}
need = limit - len(personal)
top_rows = get_global_top(limit + len(shown_ids), exclude_user_id=user_id)
padding = [dict(r, source="global")
           for r in top_rows if r["game_id"] not in shown_ids][:need]
return personal + padding
```
Если личных меньше `limit` (мало непросмотренных игр со знакомыми тегами) —
добиваем глобальным топом:
- `shown_ids` — `set` (множество) id уже отобранных личных;
- `get_global_top` с запасом, исключая на стороне БД уже оценённые;
- в Python выкидываем уже показанные (`not in shown_ids`), берём сколько не
  хватает (`[:need]`), помечаем `source="global"`.

Так нет дублей и нет уже оценённых игр.

### Итог: поле `source`

Каждая строка получает `source = 'personal' | 'global'`. По нему `index.html`
выбирает подпись блока («На основе ваших оценок» / «Популярное сейчас») и
карточки («✨ лично для вас» / «⭐ avg / 10»).

### Как три функции связаны

```
гость на главной ───────────────► get_global_top()            → «Популярное сейчас»

залогинен на главной ─► get_recommendations()
                          ├─ оценок < 3 ─────► get_global_top(exclude=я)  → source='global'
                          ├─ оценок ≥ 3 ─────► CTE taste/candidates/scored → source='personal'
                          └─ не хватило ─────► + get_global_top(exclude=я) → source='global'

карточка игры ──────────────────► get_similar_games()         → «Похожие игры»
```

`get_global_top` — «рабочая лошадка» (холодный старт + добивка);
`get_similar_games` — независимая, только для карточки.

---

## 7. Админка: транзакции

Четыре функции: вспомогательная `_clean_names`, читающая `get_game_for_edit` и
две пишущие в транзакции — `create_game`, `update_game`.

### Что такое транзакция и причём `with`

Обе пишущие функции построены вокруг (`db.py:712`, `db.py:563`):

```python
with get_connection() as conn:      # открыли соединение
    with conn.cursor() as cur:      # открыли курсор
        ... много INSERT/UPDATE/DELETE ...
    # ← выходим из блока conn
```

**Транзакция** — группа операций «всё или ничего» (буква **A** в ACID —
атомарность). В psycopg 3 при **выходе из блока `with get_connection() as conn:`**:
- ошибок не было → автоматический `COMMIT` (зафиксировать изменения);
- было исключение → автоматический `ROLLBACK` (откатить всё).

**Зачем критично.** Создание игры — много шагов (dev, игра, новые теги, связи).
Без транзакции при падении на середине осталась бы «полу-игра» — запись без
жанров и тегов, мусор. С транзакцией: упали на любом шаге → `ROLLBACK` сотрёт и
уже вставленную игру. Это **главный пример ACID** в проекте.

### `_clean_names(names)` (`db.py:669-680`)

Чистый Python (без SQL). Срезает пробелы, выкидывает пустые строки и дубликаты
(через `set`), сохраняя порядок. `_` в начале имени — «внутренняя функция».
**Зачем:** подчистить списки «новых» имён перед `INSERT`. Это второй слой чистки
(первый — `parse_new_names` в `app.py`).

### `get_game_for_edit(game_id)` (`db.py:499-535`)

**Читающая** (без транзакции), для GET-части `/admin/edit_game/<id>`. Делает
4 простых `SELECT`:

```python
game_sql = "SELECT game_id, title, release_date, description, developer_id, publisher_id FROM games WHERE game_id = %s"
genre_ids_sql    = "SELECT genre_id    FROM game_genres    WHERE game_id = %s"
tag_ids_sql      = "SELECT tag_id      FROM game_tags      WHERE game_id = %s"
platform_ids_sql = "SELECT platform_id FROM game_platforms WHERE game_id = %s"
```
- первый достаёт поля игры; нет игры (`fetchone()` → `None`) → функция вернёт
  `None`, маршрут сделает flash + redirect (`app.py:372`);
- три следующих достают **списки id** текущих жанров/тегов/платформ:
  `game["genre_ids"] = [r["genre_id"] for r in cur.fetchall()]`.

**Зачем списки id** (а не имена, как в `get_game_by_id`): данные идут в форму с
**чекбоксами**, шаблон ставит галочку через `{% if genre.genre_id in
game.genre_ids %}checked{% endif %}`. По id сравнивать надёжнее, чем по имени.

### `create_game(...)` (`db.py:683-809`)

Внутри транзакции — 4 блока.

**a) Разрешить dev/pub (`db.py:715-732`)** — «новое имя важнее выбранного id»:

```python
dev_name = new_developer_name.strip() if new_developer_name else ""
if dev_name:
    cur.execute("INSERT INTO developers (name) VALUES (%s) RETURNING developer_id", (dev_name,))
    developer_id = cur.fetchone()["developer_id"]
```
Если админ вписал нового разработчика — вставляем и **перезаписываем**
`developer_id`. Иначе оставляем выбранный (или `None`). То же для издателя.

**c) Вставить игру (`db.py:734-747`):**
```python
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (%s, %s, %s, %s, %s) RETURNING game_id
```
`RETURNING game_id` сразу даёт id новой игры — он нужен дальше для связей.

**b) Найти-или-создать жанры/теги/платформы (`db.py:749-786`)** — **find-or-create**:
```python
all_genre_ids = list(genre_ids)          # начинаем с выбранных чекбоксами
for name in new_genre_names:
    cur.execute("""
        INSERT INTO genres (name) VALUES (%s)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING genre_id
    """, (name,))
    all_genre_ids.append(cur.fetchone()["genre_id"])
```
- `ON CONFLICT (name)` — «если такой `name` уже есть» (сработает `UNIQUE` на
  колонке, `schema.sql:29`);
- `DO UPDATE SET name = EXCLUDED.name` — фиктивное обновление имени на самого
  себя; `EXCLUDED.name` — значение, что пытались вставить;
- `RETURNING genre_id` — вернуть id (нового или существующего).

**Зачем `DO UPDATE`, а не `DO NOTHING`:** `DO NOTHING` при конфликте **не вернёт
строку**, и `RETURNING` дал бы пусто, а `fetchone()` упал бы. Фиктивный апдейт
гарантирует `RETURNING` в обоих случаях. Это трюк «найди или создай» одной
командой.

**d) Вставить связи (`db.py:788-805`):**
```python
for gid in set(all_genre_ids):
    cur.execute("INSERT INTO game_genres (game_id, genre_id) VALUES (%s, %s)", (game_id, gid))
```
`set(all_genre_ids)` — **дедупликация**. Если админ и поставил галочку
«open-world», и вписал «open-world» в новые теги — оба дадут один id; без `set`
вставили бы пару дважды и упали бы на `PRIMARY KEY (game_id, tag_id)`
(`schema.sql:69`).

`return game_id` (`db.py:809`) — для redirect на `/game/<new_id>`.

### `update_game(...)` (`db.py:538-666`)

Те же параметры + `game_id`. Структура как у `create_game`, **отличия в двух
местах**.

**Отличие 1 — вместо вставки игры её обновление (`db.py:585-601`):**
```python
UPDATE games SET title=%s, release_date=%s, description=%s,
    developer_id=%s, publisher_id=%s WHERE game_id=%s
```
`WHERE game_id=%s` обязателен и точечный — иначе обновили бы все игры.

**Отличие 2 — связи через «удалить и вставить заново» (`db.py:642-663`):**
```python
cur.execute("DELETE FROM game_genres   WHERE game_id = %s", (game_id,))
cur.execute("DELETE FROM game_tags     WHERE game_id = %s", (game_id,))
cur.execute("DELETE FROM game_platforms WHERE game_id = %s", (game_id,))
for gid in set(all_genre_ids):
    cur.execute("INSERT INTO game_genres (game_id, genre_id) VALUES (%s, %s)", (game_id, gid))
```
**Почему так, а не считать разницу:** связи многие-ко-многим — набор галочек.
Снести старое и записать новое — всегда корректно: одинаково работает и при
добавлении галочки, и при снятии, и при полной замене. Не нужно сравнивать
«что было / что стало».

**Не опасно ли `DELETE` без гарантии `INSERT`:** нет — всё в одной транзакции.
Если после `DELETE` упадём на `INSERT`, `ROLLBACK` откатит и `DELETE` тоже —
старые связи вернутся. Снаружи не видно момента «без связей».

### Сводка: create vs update

```
                       create_game                 update_game
──────────────────────────────────────────────────────────────────────
a) dev/pub             INSERT нового → новый id     то же
основная запись        INSERT INTO games RETURNING  UPDATE games SET … WHERE
b) жанры/теги/платф.    find-or-create (ON CONFLICT) то же
связи (m2m)            просто INSERT (через set)    DELETE всех + INSERT заново
обёртка                одна транзакция (with conn)  одна транзакция (with conn)
возврат                game_id                      ничего
```

Обе целиком атомарны: при сбое на любом шаге БД остаётся ровно как была до
вызова.

---

*Документ описывает фактическое состояние кода на момент написания. Код не
изменялся.*
