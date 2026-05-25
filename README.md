# Игровая база данных

Учебный проект по дисциплине «Базы данных».  
Каталог игр с регистрацией пользователей, поиском, оценками и рекомендациями.

## Стек

- Python 3.10+ / Flask + Jinja2
- PostgreSQL 17
- psycopg 3 (сырой SQL, без ORM)
- Werkzeug (хэширование паролей)

## Быстрый старт

```bash
# 1. Создать виртуальное окружение и установить зависимости
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Настроить переменные окружения
copy .env.example .env
# Отредактировать .env — вписать пароль PostgreSQL

# 3. Создать базу данных и применить схему
psql -U postgres -c "CREATE DATABASE gamedb;"
psql -U postgres -d gamedb -f schema.sql
psql -U postgres -d gamedb -f seed.sql

# 4. Запустить приложение
python app.py
# Открыть http://localhost:5000
```

## Архитектура

```
app.py          — Flask-маршруты (только вызовы функций из db.py)
db.py           — весь SQL (параметризованные запросы)
schema.sql      — DDL таблиц
seed.sql        — тестовые данные
templates/      — Jinja2-шаблоны
static/         — CSS
```
