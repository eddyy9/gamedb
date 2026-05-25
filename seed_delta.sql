-- =============================================================
-- seed_delta.sql — добавить данные к СУЩЕСТВУЮЩЕЙ базе
-- (если seed.sql уже применялся ранее и в базе есть Dishonored)
--
-- Применять ПОСЛЕ создания game_store_links:
--   psql -U postgres -d gamedb -f seed_delta.sql
-- =============================================================

-- -------------------------------------------------------------
-- Новые разработчики и издатели
-- -------------------------------------------------------------
INSERT INTO developers (name, country) VALUES
    ('Valve',            'USA'),
    ('FromSoftware',     'Japan'),
    ('Supergiant Games', 'USA'),
    ('Team Cherry',      'Australia');

INSERT INTO publishers (name, country) VALUES
    ('Valve',                      'USA'),
    ('Bandai Namco Entertainment', 'Japan'),
    ('Supergiant Games',           'USA'),
    ('Team Cherry',                'Australia');

-- Новые платформы (UNIQUE — пропустить дубли)
INSERT INTO platforms (name) VALUES
    ('PlayStation 5'),
    ('Nintendo Switch')
ON CONFLICT (name) DO NOTHING;

-- Новые жанры
INSERT INTO genres (name) VALUES
    ('Puzzle'),
    ('Platformer')
ON CONFLICT (name) DO NOTHING;

-- Новые теги
INSERT INTO tags (name) VALUES
    ('co-op'),
    ('challenging'),
    ('indie'),
    ('atmospheric'),
    ('sci-fi'),
    ('roguelite')
ON CONFLICT (name) DO NOTHING;

-- -------------------------------------------------------------
-- Новые игры (developer_id / publisher_id — по имени)
-- -------------------------------------------------------------
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES
    ('The Witcher 3: Wild Hunt',
     '2015-05-19',
     'Масштабная ролевая игра в открытом мире. Ведьмак Геральт ищет свою приёмную дочь Цири '
     'в мире, раздираемом войной. Богатейший нарратив, живой открытый мир '
     'и сотни часов квестов.',
     (SELECT developer_id FROM developers WHERE name = 'CD Projekt Red'),
     (SELECT publisher_id FROM publishers WHERE name  = 'CD Projekt')),

    ('Cyberpunk 2077',
     '2020-12-10',
     'RPG-экшен в антиутопическом мегаполисе Найт-Сити. Игрок управляет наёмником V, '
     'охотящимся за уникальным нейроимплантом с цифровым духом легендарного рокера '
     'Джонни Сильверхенда.',
     (SELECT developer_id FROM developers WHERE name = 'CD Projekt Red'),
     (SELECT publisher_id FROM publishers WHERE name  = 'CD Projekt')),

    ('Portal 2',
     '2011-04-19',
     'Головоломка от первого лица с порталами. Игрок проходит испытательные камеры, '
     'используя портальную пушку для решения пространственных задач. '
     'Блестящий кооперативный режим и незабываемый ИИ-антагонист GLaDOS.',
     (SELECT developer_id FROM developers WHERE name = 'Valve'),
     (SELECT publisher_id FROM publishers WHERE name  = 'Valve')),

    ('Dark Souls III',
     '2016-03-24',
     'Мрачный экшен-RPG в умирающем фэнтезийном мире. Сложный, но честный геймплей, '
     'глубокий лор и незабываемые боссы сделали серию Dark Souls культовой.',
     (SELECT developer_id FROM developers WHERE name = 'FromSoftware'),
     (SELECT publisher_id FROM publishers WHERE name  = 'Bandai Namco Entertainment')),

    ('Hades',
     '2020-09-17',
     'Рогалик-экшен: сын Аида пытается сбежать из подземного царства. '
     'Каждый забег уникален, а история раскрывается через диалоги с богами Олимпа.',
     (SELECT developer_id FROM developers WHERE name = 'Supergiant Games'),
     (SELECT publisher_id FROM publishers WHERE name  = 'Supergiant Games')),

    ('Hollow Knight',
     '2017-02-24',
     'Метроидвания в огромном подземном королевстве жуков. Исследование, сложные сражения, '
     'потрясающий рисованный арт-дизайн и меланхоличная атмосфера угасающего мира.',
     (SELECT developer_id FROM developers WHERE name = 'Team Cherry'),
     (SELECT publisher_id FROM publishers WHERE name  = 'Team Cherry')),

    ('Sekiro: Shadows Die Twice',
     '2019-03-22',
     'Экшен от третьего лица в средневековой Японии эпохи Сэнгоку. '
     'Игрок управляет ниндзя Волком. Акцент на ритмичном фехтовании и сломе стойки противника.',
     (SELECT developer_id FROM developers WHERE name = 'FromSoftware'),
     (SELECT publisher_id FROM publishers WHERE name  = 'Bandai Namco Entertainment'));

-- -------------------------------------------------------------
-- Платформы для новых игр (по имени)
-- -------------------------------------------------------------
INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'The Witcher 3: Wild Hunt' AND p.name IN ('PC','PlayStation 4','Xbox One');

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Cyberpunk 2077' AND p.name IN ('PC','PlayStation 4','Xbox One','PlayStation 5');

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Portal 2' AND p.name = 'PC';

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Dark Souls III' AND p.name IN ('PC','PlayStation 4','Xbox One');

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Hades' AND p.name IN ('PC','Nintendo Switch');

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Hollow Knight' AND p.name IN ('PC','Nintendo Switch');

INSERT INTO game_platforms (game_id, platform_id)
SELECT g.game_id, p.platform_id FROM games g, platforms p
WHERE g.title = 'Sekiro: Shadows Die Twice' AND p.name IN ('PC','PlayStation 4','Xbox One');

-- -------------------------------------------------------------
-- Жанры для новых игр
-- -------------------------------------------------------------
INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'The Witcher 3: Wild Hunt' AND gen.name IN ('Action','RPG');

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Cyberpunk 2077' AND gen.name IN ('Action','RPG');

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Portal 2' AND gen.name = 'Puzzle';

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Dark Souls III' AND gen.name IN ('Action','RPG');

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Hades' AND gen.name IN ('Action','RPG');

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Hollow Knight' AND gen.name IN ('Action','Platformer');

INSERT INTO game_genres (game_id, genre_id)
SELECT g.game_id, gen.genre_id FROM games g, genres gen
WHERE g.title = 'Sekiro: Shadows Die Twice' AND gen.name = 'Action';

-- -------------------------------------------------------------
-- Теги для новых игр
-- -------------------------------------------------------------
INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'The Witcher 3: Wild Hunt' AND t.name IN ('open-world','story-rich','dark');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Cyberpunk 2077' AND t.name IN ('open-world','story-rich','cyberpunk');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Portal 2' AND t.name IN ('co-op','sci-fi');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Dark Souls III' AND t.name IN ('dark','challenging','atmospheric');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Hades' AND t.name IN ('atmospheric','roguelite');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Hollow Knight' AND t.name IN ('dark','indie','atmospheric');

INSERT INTO game_tags (game_id, tag_id)
SELECT g.game_id, t.tag_id FROM games g, tags t
WHERE g.title = 'Sekiro: Shadows Die Twice' AND t.name IN ('dark','challenging','atmospheric');

-- -------------------------------------------------------------
-- Ссылка Steam для Dishonored (ранее не было)
-- -------------------------------------------------------------
INSERT INTO game_store_links (game_id, store_name, url)
SELECT game_id, 'Steam', 'https://store.steampowered.com/app/205100/Dishonored/'
FROM games WHERE title = 'Dishonored';

-- Ссылки Steam для новых игр
INSERT INTO game_store_links (game_id, store_name, url)
SELECT g.game_id, 'Steam', l.url FROM games g
JOIN (VALUES
    ('The Witcher 3: Wild Hunt',  'https://store.steampowered.com/app/292030/'),
    ('Cyberpunk 2077',            'https://store.steampowered.com/app/1091500/'),
    ('Portal 2',                  'https://store.steampowered.com/app/620/'),
    ('Dark Souls III',            'https://store.steampowered.com/app/374320/'),
    ('Hades',                     'https://store.steampowered.com/app/1145360/'),
    ('Hollow Knight',             'https://store.steampowered.com/app/367520/'),
    ('Sekiro: Shadows Die Twice', 'https://store.steampowered.com/app/814380/')
) AS l(title, url) ON g.title = l.title;
