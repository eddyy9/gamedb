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

- **Весь SQL — только в `db.py`**, в виде именованных функций (`get_all_games`, `search_games` и т.д.). Маршруты Flask SQL не пишут.
- **Все запросы — параметризованные** (защита от SQL-инъекций).
- **Без ORM** — голый psycopg 3, это учебный проект по курсу «Базы данных».
- **Без Docker, без async, без blueprints** — один простой `app.py` до тех пор, пока проект не вырастет.
- **Серверный рендеринг** через Jinja2, без отдельного фронтенда.
- **Пароли** хранятся только как хэши (Werkzeug), в коде паролей нет.
- **Конфиг** — только через `.env`, `.env.example` в репозитории, `.env` в `.gitignore`.

---

## Что было опробовано и оказалось неэффективным

| Проблема | Причина | Решение |
|----------|---------|---------|
| `python` не работал в терминале | Windows Store создала заглушку `python.exe` в WindowsApps, которая перехватывала вызов и открывала магазин вместо реального Python | Отключили псевдонимы в «Параметры → Приложения → Псевдонимы запуска» |
| `python` и `psql` не находились после установки | Пути к `Python313\`, `Python313\Scripts\`, `PostgreSQL\17\bin\` не были добавлены в PATH | Добавили все три пути в PATH пользователя через PowerShell (`[Environment]::SetEnvironmentVariable`) |
| `psql` не работал в новом вызове PowerShell | PATH обновляется только для новых процессов; в текущей сессии нужно перезагружать вручную | В каждом вызове добавляем `$env:Path = [Environment]::GetEnvironmentVariable(...)` |
| Пароль psql спрашивался интерактивно | psql по умолчанию требует ввода | Используем `$env:PGPASSWORD = "..."` перед вызовом psql |

---

## Структура проекта

```
проект БД/
├── app.py               # Flask-маршруты
├── db.py                # Слой БД: get_connection(), get_all_games()
├── schema.sql           # DDL 11 таблиц
├── seed.sql             # Тестовые данные (Dishonored)
├── requirements.txt     # Зафиксированные зависимости
├── .env                 # Конфиг (не в git)
├── .env.example         # Шаблон конфига
├── .gitignore
├── README.md
├── PROJECT_LOG.md       # Этот файл
├── templates/
│   ├── base.html        # Навигация, подвал
│   └── index.html       # Список игр
├── static/
│   └── style.css        # Тёмная тема
└── venv/                # Виртуальное окружение (не в git)
```

---

## Схема базы данных

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

### Пользователи
- `users(user_id PK, username UNIQUE, email UNIQUE, password_hash, avatar_emoji, created_at)`
- `ratings(user_id FK, game_id FK, score CHECK 1..10, created_at)` — PK составной

### Заглушки (в schema.sql, закомментированы)
- `reviews`, `achievements`, `user_achievements` — добавим позже

---

## Текущее состояние проекта

**Этап: Фундамент готов и работает.**

- [x] Окружение настроено (Python 3.13, PostgreSQL 17, venv, PATH)
- [x] Структура файлов создана
- [x] Зависимости установлены в venv
- [x] `schema.sql` применён (11 таблиц)
- [x] `seed.sql` применён (Dishonored + связи)
- [x] Цепочка браузер → Flask → db.py → PostgreSQL работает
- [x] Страница `/` отображает список игр

**Проверено вручную:** на `http://localhost:5000` отображается карточка Dishonored с разработчиком и описанием.

---

## Следующие шаги (в порядке приоритета)

### Ближайшие (следующая сессия)
1. **Страница игры** `/game/<id>` — полная карточка с жанрами, тегами, платформами, средней оценкой. Новая функция `db.get_game_by_id(game_id)`.
2. **Поиск** — форма на главной, маршрут `/search?q=...`, функция `db.search_games(query)` с `ILIKE`.
3. **Добавить игр в seed.sql** — чтобы каталог выглядел как каталог.

### Средняя очередь
4. **Регистрация и логин** — `/register`, `/login`, `/logout`, сессии Flask, хэширование Werkzeug. Новые функции `db.create_user()`, `db.get_user_by_username()`.
5. **Оценки** — форма 1–10 на странице игры, маршрут `/rate/<game_id>`, функция `db.set_rating()`. Показывать среднюю оценку.
6. **Рекомендации по тегам** — на странице игры блок «Похожие игры» через JOIN по тегам.

### Поздняя очередь
7. `reviews` — текстовые отзывы.
8. `achievements` / `user_achievements`.
9. Пагинация каталога.
10. Страница профиля пользователя.

---

## Как запустить проект с нуля (для справки)

```powershell
# В папке проекта
venv\Scripts\activate
python app.py
# Открыть http://localhost:5000
```

База данных уже создана и заполнена. Повторно применять SQL не нужно.
