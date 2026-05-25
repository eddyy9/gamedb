-- =============================================================
-- Game Database — тестовые данные
-- Применять ПОСЛЕ schema.sql:
--   psql -U postgres -d gamedb -f seed.sql
-- =============================================================

-- Разработчики
INSERT INTO developers (name, country) VALUES
    ('Arkane Studios', 'France'),
    ('CD Projekt Red', 'Poland');

-- Издатели
INSERT INTO publishers (name, country) VALUES
    ('Bethesda Softworks', 'USA'),
    ('CD Projekt', 'Poland');

-- Платформы
INSERT INTO platforms (name) VALUES
    ('PC'),
    ('PlayStation 4'),
    ('Xbox One');

-- Жанры
INSERT INTO genres (name) VALUES
    ('Action'),
    ('Stealth'),
    ('RPG');

-- Теги
INSERT INTO tags (name) VALUES
    ('open-world'),
    ('story-rich'),
    ('steampunk'),
    ('dark'),
    ('cyberpunk');

-- Игра: Dishonored
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Dishonored',
    '2012-10-09',
    'Стелс-экшен от первого лица в стимпанк-городе Дануолл. '
    'Игрок управляет Корво Аттано — телохранителем, ложно обвинённым в убийстве. '
    'Игра предлагает несколько путей прохождения: от скрытного до агрессивного.',
    1,  -- Arkane Studios
    1   -- Bethesda Softworks
);

-- Связи Dishonored (game_id = 1)
INSERT INTO game_platforms (game_id, platform_id) VALUES (1, 1), (1, 2), (1, 3);
INSERT INTO game_genres   (game_id, genre_id)    VALUES (1, 1), (1, 2);
INSERT INTO game_tags     (game_id, tag_id)       VALUES (1, 2), (1, 3), (1, 4);
