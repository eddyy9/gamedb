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
    # Основная информация + средняя оценка
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

            game = dict(row)  # делаем мутабельным

            cur.execute(genres_sql, (game_id,))
            game["genres"] = [r["name"] for r in cur.fetchall()]

            cur.execute(tags_sql, (game_id,))
            game["tags"] = [r["name"] for r in cur.fetchall()]

            cur.execute(platforms_sql, (game_id,))
            game["platforms"] = [r["name"] for r in cur.fetchall()]

            # game_store_links появится после применения Phase 2 SQL;
            # до этого возвращаем пустой список, чтобы страница не ломалась.
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
    """Ищет игры по названию (ILIKE, без учёта регистра).
    Возвращает список с базовой информацией (как get_all_games).
    """
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
