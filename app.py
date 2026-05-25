import os
from flask import Flask, render_template
from dotenv import load_dotenv
import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")


@app.route("/")
def index():
    games = db.get_all_games()
    return render_template("index.html", games=games)


if __name__ == "__main__":
    app.run(debug=True)
