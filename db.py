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
