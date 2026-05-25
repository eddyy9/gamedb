import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "gamedb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


# ──────────────────────────────────────────────────────────────
# Каталог
# ──────────────────────────────────────────────────────────────

def get_all_games():
    """Возвращает все игры с именами разработчика и издателя."""
    sql = """
        SELECT
            g.game_id,
            g.title,
            g.release_date,
            g.description,
            d.name AS developer,
            p.name AS publisher
        FROM games g
        LEFT JOIN developers d USING (developer_id)
        LEFT JOIN publishers  p USING (publisher_id)
        ORDER BY g.title
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def get_game_by_id(game_id):
    """Возвращает полную карточку игры: разработчик, издатель,
    жанры, теги, платформы, средняя оценка, ссылки на магазины.
    Возвращает None, если игра не найдена.
    """
    main_sql = """
        SELECT
            g.game_id,
            g.title,
            g.release_date,
            g.description,
            d.name    AS developer,
            d.country AS developer_country,
            p.name    AS publisher,
            p.country AS publisher_country,
            ROUND(AVG(r.score), 1) AS avg_score,
            COUNT(r.score)         AS ratings_count
        FROM games g
        LEFT JOIN developers d USING (developer_id)
        LEFT JOIN publishers  p USING (publisher_id)
        LEFT JOIN ratings     r USING (game_id)
        WHERE g.game_id = %s
        GROUP BY g.game_id, d.name, d.country, p.name, p.country
    """
    genres_sql = """
        SELECT gen.name
        FROM game_genres gg
        JOIN genres gen USING (genre_id)
        WHERE gg.game_id = %s
        ORDER BY gen.name
    """
    tags_sql = """
        SELECT t.name
        FROM game_tags gt
        JOIN tags t USING (tag_id)
        WHERE gt.game_id = %s
        ORDER BY t.name
    """
    platforms_sql = """
        SELECT pl.name
        FROM game_platforms gp
        JOIN platforms pl USING (platform_id)
        WHERE gp.game_id = %s
        ORDER BY pl.name
    """
    store_links_sql = """
        SELECT store_name, url
        FROM game_store_links
        WHERE game_id = %s
        ORDER BY store_name
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(main_sql, (game_id,))
            row = cur.fetchone()
            if row is None:
                return None

            game = dict(row)

            cur.execute(genres_sql, (game_id,))
            game["genres"] = [r["name"] for r in cur.fetchall()]

            cur.execute(tags_sql, (game_id,))
            game["tags"] = [r["name"] for r in cur.fetchall()]

            cur.execute(platforms_sql, (game_id,))
            game["platforms"] = [r["name"] for r in cur.fetchall()]

            try:
                cur.execute(store_links_sql, (game_id,))
                game["store_links"] = cur.fetchall()
            except Exception:
                game["store_links"] = []

            return game


# ──────────────────────────────────────────────────────────────
# Поиск
# ──────────────────────────────────────────────────────────────

def search_games(query):
    """Ищет игры по названию (ILIKE, без учёта регистра)."""
    sql = """
        SELECT
            g.game_id,
            g.title,
            g.release_date,
            g.description,
            d.name AS developer,
            p.name AS publisher
        FROM games g
        LEFT JOIN developers d USING (developer_id)
        LEFT JOIN publishers  p USING (publisher_id)
        WHERE g.title ILIKE %s
        ORDER BY g.title
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"%{query}%",))
            return cur.fetchall()


# ──────────────────────────────────────────────────────────────
# Пользователи
# ──────────────────────────────────────────────────────────────

def create_user(username, email, password_hash):
    """Создаёт нового пользователя. Возвращает user_id.
    Бросает psycopg.errors.UniqueViolation при дубликате username/email.
    """
    sql = """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING user_id
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (username, email, password_hash))
            return cur.fetchone()["user_id"]


def get_user_by_username(username):
    """Возвращает пользователя по username (для логина) или None."""
    sql = """
        SELECT user_id, username, email, password_hash, avatar_emoji
        FROM users
        WHERE username = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()


def get_user_by_id(user_id):
    """Возвращает пользователя по user_id (для сессии) или None."""
    sql = """
        SELECT user_id, username, email, avatar_emoji, created_at
        FROM users
        WHERE user_id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()


# ──────────────────────────────────────────────────────────────
# Оценки
# ──────────────────────────────────────────────────────────────

def set_rating(user_id, game_id, score):
    """Создаёт или обновляет оценку (INSERT … ON CONFLICT DO UPDATE)."""
    sql = """
        INSERT INTO ratings (user_id, game_id, score)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, game_id)
        DO UPDATE SET score = EXCLUDED.score, created_at = now()
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, game_id, score))


def get_user_rating(user_id, game_id):
    """Возвращает оценку пользователя для игры или None."""
    sql = "SELECT score FROM ratings WHERE user_id = %s AND game_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, game_id))
            row = cur.fetchone()
            return row["score"] if row else None


# ──────────────────────────────────────────────────────────────
# Профиль пользователя
# ──────────────────────────────────────────────────────────────

def get_user_ratings(user_id):
    """Возвращает все игры, оценённые пользователем.
    ORDER BY score DESC, title.
    """
    sql = """
        SELECT
            g.game_id,
            g.title,
            r.score,
            r.created_at
        FROM ratings r
        JOIN games g USING (game_id)
        WHERE r.user_id = %s
        ORDER BY r.score DESC, g.title
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()


def get_user_stats(user_id):
    """Возвращает статистику пользователя: сколько игр оценено и его
    средняя оценка. avg_score_given = None, если оценок нет.
    """
    sql = """
        SELECT
            COUNT(*)               AS games_rated,
            ROUND(AVG(score), 1)   AS avg_score_given
        FROM ratings
        WHERE user_id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()


# ──────────────────────────────────────────────────────────────
# Каталог: справочники и фильтрация
# ──────────────────────────────────────────────────────────────

def get_all_genres():
    """Все жанры для выпадающего списка."""
    sql = "SELECT genre_id, name FROM genres ORDER BY name"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def get_all_tags():
    """Все теги для выпадающего списка."""
    sql = "SELECT tag_id, name FROM tags ORDER BY name"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def get_games_filtered(genre_id=None, tag_id=None):
    """Возвращает игры с опциональной фильтрацией по жанру и/или тегу.

    Техника: LEFT JOIN с условием на id в ON-клаузе плюс WHERE-проверка
    «IS NULL или совпало». Параметризовано, без склейки строк SQL.
    Оба условия применяются как AND.
    """
    sql = """
        SELECT DISTINCT
            g.game_id,
            g.title,
            g.release_date,
            g.description,
            d.name AS developer,
            p.name AS publisher
        FROM games g
        LEFT JOIN developers d USING (developer_id)
        LEFT JOIN publishers  p USING (publisher_id)
        LEFT JOIN game_genres gg ON g.game_id = gg.game_id AND gg.genre_id = %s
        LEFT JOIN game_tags   gt ON g.game_id = gt.game_id AND gt.tag_id   = %s
        WHERE (%s::int IS NULL OR gg.genre_id IS NOT NULL)
          AND (%s::int IS NULL OR gt.tag_id   IS NOT NULL)
        ORDER BY g.title
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (genre_id, tag_id, genre_id, tag_id))
            return cur.fetchall()


# ──────────────────────────────────────────────────────────────
# Рекомендации
# ──────────────────────────────────────────────────────────────

def get_similar_games(game_id, limit=4):
    """Возвращает до limit игр с общими тегами.
    Сортировка: больше совпадающих тегов — выше.
    """
    sql = """
        SELECT
            g.game_id,
            g.title,
            g.release_date,
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
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (game_id, game_id, limit))
            return cur.fetchall()


def get_global_top(limit=4):
    """Игры с наивысшей средней оценкой от всех пользователей.
    При равенстве AVG — больше оценок выше (ORDER BY avg DESC, count DESC).
    Запасной вариант для холодного старта.
    """
    sql = """
        SELECT
            g.game_id,
            g.title,
            d.name                 AS developer,
            ROUND(AVG(r.score), 1) AS avg_score,
            COUNT(r.score)         AS ratings_count
        FROM games g
        JOIN ratings r USING (game_id)
        LEFT JOIN developers d USING (developer_id)
        GROUP BY g.game_id, g.title, d.name
        ORDER BY avg_score DESC, ratings_count DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()


def get_recommendations(user_id, limit=4):
    """Персональные рекомендации по профилю вкуса пользователя.

    Алгоритм:
      1. Если у пользователя < 3 оценок → вернуть global top (холодный старт).
      2. Иначе: CTE-запрос taste/candidates/scored — tag-affinity scoring
         (affinity = AVG(score) - 5.5 по каждому тегу).
      3. Если personal-результатов < limit — дополнить global top, исключая
         уже показанные и оценённые игры.
    Каждая строка получает поле source = 'personal' | 'global'.
    """
    # Считаем оценки пользователя
    count_sql = "SELECT COUNT(*) AS cnt FROM ratings WHERE user_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, (user_id,))
            cnt = cur.fetchone()["cnt"]

    if cnt < 3:
        rows = get_global_top(limit)
        return [dict(r, source="global") for r in rows]

    # Персональные рекомендации через CTE
    personal_sql = """
        WITH taste AS (
            SELECT gt.tag_id,
                   AVG(r.score) - 5.5 AS affinity
            FROM ratings r
            JOIN game_tags gt ON gt.game_id = r.game_id
            WHERE r.user_id = %s
            GROUP BY gt.tag_id
        ),
        candidates AS (
            SELECT g.game_id
            FROM games g
            WHERE NOT EXISTS (
                SELECT 1 FROM ratings r
                WHERE r.user_id = %s AND r.game_id = g.game_id
            )
        ),
        scored AS (
            SELECT c.game_id,
                   SUM(t.affinity) AS rec_score
            FROM candidates c
            JOIN game_tags gt ON gt.game_id = c.game_id
            JOIN taste     t  ON t.tag_id   = gt.tag_id
            GROUP BY c.game_id
        )
        SELECT
            g.game_id,
            g.title,
            d.name      AS developer,
            s.rec_score
        FROM scored s
        JOIN games g ON g.game_id = s.game_id
        LEFT JOIN developers d USING (developer_id)
        ORDER BY s.rec_score DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(personal_sql, (user_id, user_id, limit))
            personal = [dict(r, source="personal") for r in cur.fetchall()]

    if len(personal) >= limit:
        return personal

    # Дополняем global top, исключая уже показанные и оценённые игры
    shown_ids = {r["game_id"] for r in personal}

    rated_sql = "SELECT game_id FROM ratings WHERE user_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(rated_sql, (user_id,))
            rated_ids = {r["game_id"] for r in cur.fetchall()}

    exclude_ids = shown_ids | rated_ids
    need = limit - len(personal)

    # Берём global top с запасом и фильтруем в Python
    top_rows = get_global_top(limit + len(exclude_ids))
    padding = [
        dict(r, source="global")
        for r in top_rows
        if r["game_id"] not in exclude_ids
    ][:need]

    return personal + padding
