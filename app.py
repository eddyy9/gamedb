import os
from flask import Flask, render_template, request, abort
from dotenv import load_dotenv
import db

load_dotenv()

app = Flask(__name__)

# ── Секретный ключ (обязательно через .env) ──────────────────
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ── Безопасные настройки сессионных куки ─────────────────────
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# На проде переключить в true через переменную SESSION_COOKIE_SECURE=true
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)


# ── Маршруты ─────────────────────────────────────────────────

@app.route("/")
def index():
    games = db.get_all_games()
    return render_template("index.html", games=games)


@app.route("/game/<int:game_id>")
def game_detail(game_id):
    game = db.get_game_by_id(game_id)
    if game is None:
        abort(404)
    return render_template("game.html", game=game)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    games = []
    if query:
        from validators import validate_search_query
        error = validate_search_query(query)
        if not error:
            games = db.search_games(query)
    return render_template("search.html", games=games, query=query)


if __name__ == "__main__":
    app.run(debug=True)
