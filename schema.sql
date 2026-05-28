-- =============================================================
-- Game Database — DDL
-- Применять: psql -U postgres -d gamedb -f schema.sql
-- =============================================================

-- -------------------------------------------------------------
-- Справочники каталога
-- -------------------------------------------------------------

CREATE TABLE developers (
    developer_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    country      VARCHAR(100)
);

CREATE TABLE publishers (
    publisher_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    country      VARCHAR(100)
);

CREATE TABLE platforms (
    platform_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE genres (
    genre_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name     VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE tags (
    tag_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name   VARCHAR(100) NOT NULL UNIQUE
);

-- -------------------------------------------------------------
-- Основная таблица игр
-- -------------------------------------------------------------

CREATE TABLE games (
    game_id      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        VARCHAR(300) NOT NULL,
    release_date DATE,
    description  TEXT,
    developer_id INT REFERENCES developers(developer_id) ON DELETE SET NULL,
    publisher_id INT REFERENCES publishers(publisher_id) ON DELETE SET NULL
);

-- -------------------------------------------------------------
-- Связующие таблицы (многие-ко-многим)
-- -------------------------------------------------------------

CREATE TABLE game_platforms (
    game_id     INT REFERENCES games(game_id)         ON DELETE CASCADE,
    platform_id INT REFERENCES platforms(platform_id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, platform_id)
);

CREATE TABLE game_genres (
    game_id  INT REFERENCES games(game_id)   ON DELETE CASCADE,
    genre_id INT REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, genre_id)
);

CREATE TABLE game_tags (
    game_id INT REFERENCES games(game_id) ON DELETE CASCADE,
    tag_id  INT REFERENCES tags(tag_id)   ON DELETE CASCADE,
    PRIMARY KEY (game_id, tag_id)
);

-- -------------------------------------------------------------
-- Ссылки на магазины (Steam, GOG, Epic и т.д.)
-- -------------------------------------------------------------

CREATE TABLE game_store_links (
    link_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id    INT  NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    store_name TEXT NOT NULL,
    url        TEXT NOT NULL
);

-- -------------------------------------------------------------
-- Пользователи
-- -------------------------------------------------------------

CREATE TABLE users (
    user_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar_emoji  VARCHAR(10)  DEFAULT '🎮',
    is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------
-- Оценки игр (1–10)
-- -------------------------------------------------------------

CREATE TABLE ratings (
    user_id    INT  REFERENCES users(user_id) ON DELETE CASCADE,
    game_id    INT  REFERENCES games(game_id) ON DELETE CASCADE,
    score      INT  NOT NULL CHECK (score BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, game_id)
);

-- =============================================================
-- Заглушки для будущих таблиц (раскомментировать по мере роста)
-- =============================================================

-- CREATE TABLE reviews (
--     review_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     user_id    INT REFERENCES users(user_id) ON DELETE CASCADE,
--     game_id    INT REFERENCES games(game_id) ON DELETE CASCADE,
--     body       TEXT NOT NULL,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
--     UNIQUE (user_id, game_id)
-- );

-- CREATE TABLE achievements (
--     achievement_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     game_id        INT REFERENCES games(game_id) ON DELETE CASCADE,
--     name           VARCHAR(200) NOT NULL,
--     description    TEXT
-- );

-- CREATE TABLE user_achievements (
--     user_id        INT REFERENCES users(user_id)              ON DELETE CASCADE,
--     achievement_id INT REFERENCES achievements(achievement_id) ON DELETE CASCADE,
--     unlocked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
--     PRIMARY KEY (user_id, achievement_id)
-- );
