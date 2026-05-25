import hmac
import os
import secrets
import psycopg.errors
from flask import (Flask, render_template, request,
                   abort, session, redirect, url_for, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from validators import (validate_username, validate_email,
                        validate_password, validate_score,
                        validate_search_query, safe_int)
import db

load_dotenv()

app = Flask(__name__)

# ── Секретный ключ ────────────────────────────────────────────
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ── Безопасные настройки сессионных куки ─────────────────────
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)


# ── CSRF ──────────────────────────────────────────────────────

def get_csrf_token() -> str:
    """Возвращает CSRF-токен из сессии; генерирует и сохраняет при первом вызове."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


@app.before_request
def check_csrf():
    """Централизованная CSRF-проверка для всех мутирующих методов.
    Сравнение через hmac.compare_digest (постоянное время, защита от timing-атак).
    GET-формы (поиск, фильтры) не проверяются.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        session_token = session.get("csrf_token", "")
        form_token    = request.form.get("csrf_token", "")
        # Пустой токен в сессии — всегда отказ
        if not session_token or not hmac.compare_digest(session_token, form_token):
            abort(400)


# ── Context processors ────────────────────────────────────────

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = db.get_user_by_id(user_id)
        return {"current_user": user}
    return {"current_user": None}


@app.context_processor
def inject_csrf():
    """Прокидывает csrf_token в каждый шаблон."""
    return {"csrf_token": get_csrf_token()}


# ── Каталог с фильтрами ───────────────────────────────────────

@app.route("/")
def index():
    genre_id = safe_int(request.args.get("genre_id"))
    tag_id   = safe_int(request.args.get("tag_id"))

    if genre_id is not None or tag_id is not None:
        games = db.get_games_filtered(genre_id=genre_id, tag_id=tag_id)
    else:
        games = db.get_all_games()

    genres = db.get_all_genres()
    tags   = db.get_all_tags()

    # Рекомендации: персональные для авторизованных, global top для гостей
    user_id = session.get("user_id")
    if user_id:
        recommendations = db.get_recommendations(user_id, limit=4)
    else:
        recommendations = [dict(r, source="global")
                           for r in db.get_global_top(limit=4)]

    return render_template("index.html",
                           games=games,
                           genres=genres,
                           tags=tags,
                           selected_genre=genre_id,
                           selected_tag=tag_id,
                           recommendations=recommendations)


# ── Карточка игры ─────────────────────────────────────────────

@app.route("/game/<int:game_id>")
def game_detail(game_id):
    game = db.get_game_by_id(game_id)
    if game is None:
        abort(404)

    user_rating = None
    user_id = session.get("user_id")
    if user_id:
        user_rating = db.get_user_rating(user_id, game_id)

    similar = db.get_similar_games(game_id, limit=4)

    return render_template("game.html",
                           game=game,
                           user_rating=user_rating,
                           similar=similar)


# ── Поиск ─────────────────────────────────────────────────────

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    games = []
    if query:
        error = validate_search_query(query)
        if not error:
            games = db.search_games(query)
    return render_template("search.html", games=games, query=query)


# ── Оценки ────────────────────────────────────────────────────

@app.route("/rate/<int:game_id>", methods=["POST"])
def rate_game(game_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Войдите, чтобы оставить оценку.", "info")
        return redirect(url_for("login"))

    score_raw = request.form.get("score", "")
    error = validate_score(score_raw)
    if error:
        flash(error, "error")
    else:
        db.set_rating(user_id, game_id, int(score_raw))
        flash(f"Оценка {score_raw} сохранена! ⭐", "success")

    return redirect(url_for("game_detail", game_id=game_id))


# ── Профиль ───────────────────────────────────────────────────

@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Войдите, чтобы просмотреть профиль.", "info")
        return redirect(url_for("login"))

    ratings = db.get_user_ratings(user_id)
    stats   = db.get_user_stats(user_id)

    return render_template("profile.html", ratings=ratings, stats=stats)


# ── Регистрация ───────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "")

        error = (validate_username(username)
                 or validate_email(email)
                 or validate_password(password))

        if not error:
            try:
                password_hash = generate_password_hash(password)
                user_id = db.create_user(username, email, password_hash)
                session["user_id"] = user_id
                flash(f"Добро пожаловать, {username}! 🎮", "success")
                return redirect(url_for("index"))
            except psycopg.errors.UniqueViolation:
                error = "Такое имя пользователя или email уже занято."
            except Exception:
                error = "Ошибка при создании аккаунта. Попробуйте ещё раз."

    return render_template("register.html", error=error)


# ── Логин ─────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.get_user_by_username(username)
        # Обобщённое сообщение — не раскрываем, что именно неверно
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Неверный логин или пароль."
        else:
            session["user_id"] = user["user_id"]
            flash(f"С возвращением, {user['username']}! 🎮", "success")
            return redirect(url_for("index"))

    return render_template("login.html", error=error)


# ── Выход ─────────────────────────────────────────────────────

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
