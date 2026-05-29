# PSQL_HANDBOOK — методичка и тренажёр по PostgreSQL на базе gamedb

> Этот файл — практическое пособие по работе с твоей базой `gamedb` через
> консольный клиент `psql`. Часть 1 — справочник команд (каждая с пояснением и
> примером на твоих реальных таблицах). Часть 2 — тренажёр из задач по
> возрастанию сложности; ответы вынесены в конец, чтобы можно было сначала решить
> самому.
>
> Все команды используют **реальные имена таблиц и столбцов** из `schema.sql`.
> Документ ничего не меняет в коде и не требует менять данные: все примеры на
> изменение/удаление обёрнуты в транзакцию с откатом.

## Что лежит в базе (быстрая карта)

12 таблиц:

- **Справочники:** `developers`, `publishers`, `platforms`, `genres`, `tags`.
- **Игры:** `games` (8 игр после `seed.sql`).
- **Связи многие-ко-многим:** `game_platforms`, `game_genres`, `game_tags`.
- **Магазины:** `game_store_links`.
- **Пользователи и оценки:** `users`, `ratings`.

> ⚠️ **Важно для задач с оценками.** `seed.sql` заполняет только каталог. Таблицы
> `users` и `ratings` поначалу **пустые** — они наполняются через сайт
> (регистрация и кнопки оценки). Поэтому запросы с `AVG(score)` / `COUNT` по
> `ratings` вернут пусто, пока ты не зарегистрируешься и не поставишь несколько
> оценок. Это нормально.

Ключевые столбцы (из `schema.sql`):

```
games(game_id, title, release_date, description, developer_id, publisher_id)
developers(developer_id, name, country)        publishers(publisher_id, name, country)
genres(genre_id, name)   tags(tag_id, name)    platforms(platform_id, name)
game_genres(game_id, genre_id)   game_tags(game_id, tag_id)   game_platforms(game_id, platform_id)
users(user_id, username, email, password_hash, avatar_emoji, is_admin, created_at)
ratings(user_id, game_id, score, created_at)   -- score CHECK 1..10, PK (user_id, game_id)
game_store_links(link_id, game_id, store_name, url)
```

---

# ЧАСТЬ 1. МЕТОДИЧКА (справочник)

## 1.1 Подключение

**`chcp 65001`** — переключить кодовую страницу терминала Windows на UTF-8.
Делается **до** запуска `psql`, чтобы кириллица (названия, описания игр) не
превращалась в «кракозябры».

```powershell
chcp 65001
```

**`psql -U postgres -d gamedb`** — запустить psql под пользователем `postgres`
и сразу подключиться к базе `gamedb`. Спросит пароль.

```powershell
psql -U postgres -d gamedb
```

> `-U` — имя пользователя БД, `-d` — имя базы. Под `postgres` можно всё (это
> суперпользователь); приложение же ходит под ограниченной ролью `gamedb_app`.

**Как выглядит приглашение.** После подключения видишь:

```
gamedb=#
```

`gamedb` — текущая база, `#` — ты суперпользователь (у обычного было бы `>`).
Если приглашение сменилось на `gamedb-#` — ты не закрыл команду точкой с запятой,
psql ждёт продолжения.

**Главное правило:**
- **SQL-команды заканчиваются `;`** (точкой с запятой). Без неё psql думает, что
  ты ещё не дописал, и не выполняет.
- **Мета-команды psql начинаются с `\`** (обратный слеш) и `;` **не** требуют.

## 1.2 Мета-команды psql (служебные, начинаются с `\`)

**`\dt`** — список таблиц текущей базы.
```
gamedb=# \dt
```
Покажет `developers`, `games`, `ratings`, `users` и т.д.

**`\d games`** — структура конкретной таблицы: столбцы, типы, ограничения,
индексы, внешние ключи.
```
gamedb=# \d games
```
Увидишь `game_id integer not null`, `title character varying(300)`, внешние ключи
на `developers` и `publishers`.

**`\d ratings`** — удобно посмотреть, как выглядят ограничения `CHECK (score
BETWEEN 1 AND 10)` и составной первичный ключ `(user_id, game_id)`.

**`\du`** — список ролей (пользователей БД). Здесь видно `postgres` и `gamedb_app`.

**`\l`** — список всех баз на сервере (среди них `gamedb`).

**`\x`** — переключатель вертикального вывода (expanded). Удобно, когда у строки
много столбцов и они не влезают по ширине: каждое поле печатается на своей строке.
Повторный `\x` выключает.
```
gamedb=# \x
Expanded display is on.
gamedb=# SELECT * FROM games WHERE game_id = 2;
```

**`\?`** — справка по мета-командам psql (весь список `\`-команд).

**`\h`** — справка по SQL. `\h SELECT` покажет синтаксис конкретной команды.
```
gamedb=# \h INSERT
```

**`\q`** — выход из psql обратно в терминал.

## 1.3 Просмотр данных (SELECT)

**`SELECT *`** — выбрать все столбцы.
```sql
SELECT * FROM genres;
```

**Выбор конкретных столбцов** — перечисли их через запятую (быстрее и читаемее).
```sql
SELECT title, release_date FROM games;
```

**`WHERE`** — условие отбора строк.
```sql
SELECT title, release_date FROM games WHERE developer_id = 4;
```
(игры FromSoftware — Dark Souls III и Sekiro)

**`ORDER BY`** — сортировка. `ASC` по возрастанию (по умолчанию), `DESC` по
убыванию.
```sql
SELECT title, release_date FROM games ORDER BY release_date DESC;
```

**`LIMIT`** — ограничить число строк.
```sql
SELECT title FROM games ORDER BY title LIMIT 3;
```

**`COUNT`** — посчитать строки.
```sql
SELECT COUNT(*) FROM games;        -- 8
```

**`ILIKE`** — поиск по тексту без учёта регистра; `%` означает «любой текст».
```sql
SELECT title FROM games WHERE title ILIKE '%dark%';   -- Dark Souls III
```
(`LIKE` — то же, но с учётом регистра)

## 1.4 Связи между таблицами (JOIN)

**`JOIN`** склеивает строки двух таблиц по условию. Игра хранит только
`developer_id` (число) — чтобы получить имя студии, нужно подключить таблицу
`developers`.

**Игра + разработчик:**
```sql
SELECT g.title, d.name AS developer
FROM games g
JOIN developers d ON g.developer_id = d.developer_id
ORDER BY g.title;
```

**Игра + издатель:**
```sql
SELECT g.title, p.name AS publisher
FROM games g
JOIN publishers p ON g.publisher_id = p.publisher_id
ORDER BY g.title;
```

> `g` и `d` — псевдонимы (алиасы) таблиц, чтобы писать короче. `AS developer` —
> переименовать столбец в выводе.
>
> `JOIN` (он же `INNER JOIN`) оставит только строки с совпадением. Если хочешь
> видеть игру даже без указанного разработчика — `LEFT JOIN` (так и сделано в
> коде приложения, `db.py`).

**Платформы конкретной игры** (через связующую таблицу):
```sql
SELECT g.title, pl.name AS platform
FROM games g
JOIN game_platforms gp ON g.game_id = gp.game_id
JOIN platforms pl      ON gp.platform_id = pl.platform_id
WHERE g.title = 'Hades';
```

## 1.5 Агрегаты (GROUP BY, HAVING)

Агрегатные функции считают одно число по группе строк: `COUNT` (сколько),
`AVG` (среднее), `SUM`, `MIN`, `MAX`, `ROUND` (округление).

**Сколько игр у каждого разработчика** (`GROUP BY` группирует строки):
```sql
SELECT d.name AS developer, COUNT(*) AS games_count
FROM games g
JOIN developers d ON g.developer_id = d.developer_id
GROUP BY d.name
ORDER BY games_count DESC;
```
(FromSoftware — 2, у остальных по 1)

**`HAVING`** — это «WHERE для агрегатов»: фильтрует уже посчитанные группы.
Например, разработчики, у кого больше одной игры:
```sql
SELECT d.name, COUNT(*) AS games_count
FROM games g
JOIN developers d ON g.developer_id = d.developer_id
GROUP BY d.name
HAVING COUNT(*) > 1;
```
> Разница: `WHERE` фильтрует строки **до** группировки, `HAVING` — группы
> **после**.

**Средняя оценка по играм** (нужны данные в `ratings` — поставь оценки через
сайт):
```sql
SELECT g.title,
       ROUND(AVG(r.score), 1) AS avg_score,
       COUNT(r.score)         AS ratings_count
FROM games g
JOIN ratings r ON g.game_id = r.game_id
GROUP BY g.title
ORDER BY avg_score DESC;
```
Это ровно тот запрос, что приложение использует для «глобального топа»
(`get_global_top` в `db.py`).

## 1.6 Изменение данных (INSERT, UPDATE, DELETE)

> # ⚠️ ОГРОМНОЕ ПРЕДУПРЕЖДЕНИЕ
> **У `UPDATE` и `DELETE` ВСЕГДА должен быть `WHERE`.**
> `DELETE FROM games;` без `WHERE` сотрёт **ВСЕ** игры. `UPDATE users SET
> is_admin = TRUE;` без `WHERE` сделает админами **всех**. PostgreSQL не
> переспрашивает. Перед каждым `UPDATE`/`DELETE` проверь, что `WHERE` на месте и
> отбирает именно те строки. На тренировке оборачивай такие команды в
> `BEGIN … ROLLBACK` (см. 1.7) — тогда никакой ошибки не страшно.

**`INSERT`** — вставить строку.
```sql
INSERT INTO tags (name) VALUES ('metroidvania');
```

**`RETURNING`** — попросить БД вернуть значения вставленной (или изменённой)
строки. Удобно, чтобы сразу увидеть сгенерированный id.
```sql
INSERT INTO tags (name) VALUES ('metroidvania') RETURNING tag_id, name;
```

**`UPDATE`** — изменить существующие строки (помни про `WHERE`).
```sql
UPDATE games SET description = 'Новое описание' WHERE game_id = 4 RETURNING title;
```

**`DELETE`** — удалить строки (тоже строго с `WHERE`).
```sql
DELETE FROM tags WHERE name = 'metroidvania' RETURNING tag_id;
```

## 1.7 Транзакции (BEGIN / COMMIT / ROLLBACK)

**Транзакция** — группа операций «всё или ничего».

- **`BEGIN;`** — начать транзакцию.
- **`COMMIT;`** — зафиксировать изменения (сделать постоянными).
- **`ROLLBACK;`** — откатить, как будто ничего не было.

**Безопасный приём «посмотреть и откатить».** Хочешь показать на защите, как
работает удаление, но **не** испортить данные? Оберни в `BEGIN … ROLLBACK`:

```sql
BEGIN;
DELETE FROM games WHERE title = 'Portal 2';
SELECT COUNT(*) FROM games;     -- увидишь 7: внутри транзакции игры уже нет
ROLLBACK;
SELECT COUNT(*) FROM games;     -- снова 8: откат всё вернул
```

Пока ты не сделал `COMMIT`, изменения видны только в твоей сессии. `ROLLBACK`
отменяет их полностью. Это безопасная «песочница» для демонстрации `UPDATE`,
`DELETE` и нарушений ограничений.

## 1.8 Демонстрация ограничений целостности

База сама защищает себя — это можно красиво показать. Обе демонстрации делай
внутри `BEGIN … ROLLBACK` (нужен хотя бы один зарегистрированный пользователь —
см. 1.9; считаем, что его `user_id = 1`).

**Нарушение `CHECK (score BETWEEN 1 AND 10)`** — оценка вне диапазона:
```sql
BEGIN;
INSERT INTO ratings (user_id, game_id, score) VALUES (1, 2, 11);
-- ERROR:  new row for relation "ratings" violates check constraint "ratings_score_check"
ROLLBACK;
```
БД отказала: 11 не входит в 1..10.

**Нарушение внешнего ключа (FOREIGN KEY)** — оценка несуществующей игре:
```sql
BEGIN;
INSERT INTO ratings (user_id, game_id, score) VALUES (1, 9999, 8);
-- ERROR:  insert or update on table "ratings" violates foreign key constraint
--         ... Key (game_id)=(9999) is not present in table "games".
ROLLBACK;
```
Игры с `game_id = 9999` нет в `games`, поэтому ссылку поставить нельзя.

> Вывод для защиты: правила (`CHECK`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`) живут
> в самой схеме (`schema.sql`) и срабатывают независимо от приложения — даже если
> кто-то полезет напрямую через psql.

## 1.9 Трюк с админкой (is_admin — уровень приложения)

Важно понимать разницу:
- **Роль БД** (`postgres`, `gamedb_app`) — это про права на уровне *самого
  PostgreSQL* (кто что может в базе). Видно в `\du`.
- **`is_admin`** — это **обычный столбец** в таблице `users` (тип `BOOLEAN`,
  `schema.sql:93`). Это «администратор **приложения**», а не роль БД. Приложение
  само читает этот флаг и решает, показывать ли админ-кнопки и пускать ли на
  `/admin/...`.

**Живая демонстрация (по шагам):**

1. На сайте пройди **регистрацию** обычным способом. Пароль при этом **хэшируется**
   приложением (Werkzeug) — в таблице окажется не пароль, а хэш. Проверь:
   ```sql
   SELECT user_id, username, is_admin, password_hash FROM users;
   ```
   Увидишь свой логин, `is_admin = f` (false) и длинную строку-хэш вместо пароля.

2. Выдай себе права администратора **приложения** (подставь свой логин):
   ```sql
   UPDATE users SET is_admin = TRUE WHERE username = 'ИМЯ_ПОЛЬЗОВАТЕЛЯ';
   ```
   (`WHERE` обязателен! Иначе сделаешь админами всех.)

3. Обнови страницу в браузере. В шапке появится «🛠 Добавить игру», а на карточках
   игр — «✏️ Редактировать». Права применились без перезапуска — приложение читает
   `is_admin` на каждый запрос.

> Тонкость: пароль через psql задать «по-человечески» нельзя — приложение хранит
> только хэш. Поэтому пользователя **создают через сайт**, а через psql лишь
> поднимают флаг `is_admin`.

## 1.10 Как посмотреть структуру базы

**Через psql** — мета-командой `\d`:
- `\dt` — все таблицы;
- `\d games` — столбцы и ограничения одной таблицы;
- `\d+ games` — то же, но подробнее (размеры, описания).

**Через графический клиент pgAdmin** (ставится вместе с PostgreSQL):
- дерево слева: **Servers → (твой сервер) → Databases → gamedb → Schemas →
  public → Tables** — там все 12 таблиц, по каждой можно раскрыть столбцы, ключи,
  ограничения;
- правый клик по базе **gamedb → ERD For Database** — pgAdmin построит
  **ER-диаграмму** прямо из живой базы: таблицы прямоугольниками, связи (внешние
  ключи) — линиями. Отлично смотрится на защите как «вот моя схема».

**Альтернатива — DBeaver** (бесплатный универсальный клиент): подключаешься к
`gamedb`, и он тоже умеет показывать таблицы и строить диаграммы связей
(вкладка «ER Diagram» у схемы/таблицы).

---

# ЧАСТЬ 2. ТРЕНАЖЁР

Реши сам, потом сверься с разделом «Ответы». Все задачи — на твоих засеянных
данных (8 игр). Задачи 11–14 на изменение данных делай внутри `BEGIN … ROLLBACK`,
чтобы база не пострадала.

**Задача 1 (разминка).** Выведи все жанры из таблицы `genres`.

**Задача 2.** Выведи названия всех игр, отсортированные по алфавиту.

**Задача 3.** Выведи название и дату выхода только тех игр, что вышли **после
31 декабря 2016 года**, сначала самые новые.

**Задача 4.** Посчитай, сколько всего игр в базе.

**Задача 5.** Найди все игры, в названии которых встречается слово «dark»
(без учёта регистра).

**Задача 6.** Выведи названия всех тегов, отсортированные по алфавиту, но не
больше 5 штук.

**Задача 7 (JOIN).** Выведи название каждой игры рядом с именем её разработчика.

**Задача 8 (JOIN + WHERE).** Выведи названия игр, изданных издателем
`CD Projekt`.

**Задача 9 (JOIN через связь).** Выведи все жанры игры `Hades`.

**Задача 10 (агрегат + GROUP BY).** Посчитай, сколько игр приходится на каждый
жанр. Выведи название жанра и число игр, по убыванию числа.

**Задача 11 (HAVING).** Выведи только те жанры, у которых **больше двух** игр.

**Задача 12 (транзакция + INSERT + RETURNING).** Внутри транзакции добавь новый
тег `soulslike` и посмотри его сгенерированный `tag_id`. Затем откати — тега в
базе остаться не должно.

**Задача 13 (демонстрация CHECK).** Покажи, что база не даёт поставить оценку 11.
Сделай это безопасно (без реального изменения данных). Считай, что есть
пользователь с `user_id = 1`.

**Задача 14 (демонстрация внешнего ключа).** Покажи, что нельзя поставить оценку
игре с `game_id = 9999` (такой игры нет). Тоже безопасно.

**Задача 15 (админ-трюк).** Напиши команду, которая выдаёт права администратора
приложения пользователю с логином `ilya`. (Помни про `WHERE`.)

---

# ОТВЕТЫ

**Ответ 1.**
```sql
SELECT * FROM genres;
```

**Ответ 2.**
```sql
SELECT title FROM games ORDER BY title;
```

**Ответ 3.**
```sql
SELECT title, release_date
FROM games
WHERE release_date > '2016-12-31'
ORDER BY release_date DESC;
```
(Sekiro 2019, Cyberpunk 2020, Hades 2020, Hollow Knight 2017)

**Ответ 4.**
```sql
SELECT COUNT(*) FROM games;     -- 8
```

**Ответ 5.**
```sql
SELECT title FROM games WHERE title ILIKE '%dark%';   -- Dark Souls III
```

**Ответ 6.**
```sql
SELECT name FROM tags ORDER BY name LIMIT 5;
```

**Ответ 7.**
```sql
SELECT g.title, d.name AS developer
FROM games g
JOIN developers d ON g.developer_id = d.developer_id
ORDER BY g.title;
```

**Ответ 8.**
```sql
SELECT g.title
FROM games g
JOIN publishers p ON g.publisher_id = p.publisher_id
WHERE p.name = 'CD Projekt';
```
(The Witcher 3: Wild Hunt, Cyberpunk 2077)

**Ответ 9.**
```sql
SELECT gen.name AS genre
FROM games g
JOIN game_genres gg ON g.game_id = gg.game_id
JOIN genres gen     ON gg.genre_id = gen.genre_id
WHERE g.title = 'Hades';
```
(Action, RPG)

**Ответ 10.**
```sql
SELECT gen.name AS genre, COUNT(*) AS games_count
FROM genres gen
JOIN game_genres gg ON gen.genre_id = gg.genre_id
GROUP BY gen.name
ORDER BY games_count DESC;
```
(Action — 7, RPG — 4, далее Stealth/Puzzle/Platformer по 1)

**Ответ 11.**
```sql
SELECT gen.name AS genre, COUNT(*) AS games_count
FROM genres gen
JOIN game_genres gg ON gen.genre_id = gg.genre_id
GROUP BY gen.name
HAVING COUNT(*) > 2;
```
(Action — 7, RPG — 4)

**Ответ 12.**
```sql
BEGIN;
INSERT INTO tags (name) VALUES ('soulslike') RETURNING tag_id, name;
ROLLBACK;
-- проверка, что тега нет:
SELECT * FROM tags WHERE name = 'soulslike';   -- 0 строк
```

**Ответ 13.**
```sql
BEGIN;
INSERT INTO ratings (user_id, game_id, score) VALUES (1, 2, 11);
-- ERROR: ... violates check constraint "ratings_score_check"
ROLLBACK;
```
> Если получишь ошибку внешнего ключа по `user_id` — значит, пользователя с
> `user_id = 1` ещё нет; сначала зарегистрируйся на сайте и подставь свой
> реальный `user_id` (узнать: `SELECT user_id, username FROM users;`).

**Ответ 14.**
```sql
BEGIN;
INSERT INTO ratings (user_id, game_id, score) VALUES (1, 9999, 8);
-- ERROR: ... violates foreign key constraint ... Key (game_id)=(9999) is not present in table "games".
ROLLBACK;
```

**Ответ 15.**
```sql
UPDATE users SET is_admin = TRUE WHERE username = 'ilya';
```
> Это реально меняет флаг (так и задумано для админ-демо). Если просто
> тренируешься и не хочешь менять — оберни в `BEGIN; … ROLLBACK;`.

---

*Документ описывает фактическую схему и данные на момент написания. Код и база
не изменялись.*
