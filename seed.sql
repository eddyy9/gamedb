-- =============================================================
-- Game Database — тестовые данные (8 игр)
-- Применять ПОСЛЕ schema.sql на чистой базе:
--   psql -U postgres -d gamedb -f seed.sql
--
-- Для добавления к существующей базе — см. seed_delta.sql
-- =============================================================

-- -------------------------------------------------------------
-- Разработчики
-- -------------------------------------------------------------
INSERT INTO developers (name, country) VALUES
    ('Arkane Studios',    'France'),      -- 1
    ('CD Projekt Red',    'Poland'),      -- 2
    ('Valve',             'USA'),         -- 3
    ('FromSoftware',      'Japan'),       -- 4
    ('Supergiant Games',  'USA'),         -- 5
    ('Team Cherry',       'Australia');   -- 6

-- -------------------------------------------------------------
-- Издатели
-- -------------------------------------------------------------
INSERT INTO publishers (name, country) VALUES
    ('Bethesda Softworks',         'USA'),     -- 1
    ('CD Projekt',                 'Poland'),  -- 2
    ('Valve',                      'USA'),     -- 3
    ('Bandai Namco Entertainment', 'Japan'),   -- 4
    ('Supergiant Games',           'USA'),     -- 5
    ('Team Cherry',                'Australia'); -- 6

-- -------------------------------------------------------------
-- Платформы
-- -------------------------------------------------------------
INSERT INTO platforms (name) VALUES
    ('PC'),               -- 1
    ('PlayStation 4'),    -- 2
    ('Xbox One'),         -- 3
    ('PlayStation 5'),    -- 4
    ('Nintendo Switch');  -- 5

-- -------------------------------------------------------------
-- Жанры
-- -------------------------------------------------------------
INSERT INTO genres (name) VALUES
    ('Action'),      -- 1
    ('Stealth'),     -- 2
    ('RPG'),         -- 3
    ('Puzzle'),      -- 4
    ('Platformer');  -- 5

-- -------------------------------------------------------------
-- Теги
-- -------------------------------------------------------------
INSERT INTO tags (name) VALUES
    ('open-world'),   -- 1
    ('story-rich'),   -- 2
    ('steampunk'),    -- 3
    ('dark'),         -- 4
    ('cyberpunk'),    -- 5
    ('co-op'),        -- 6
    ('challenging'),  -- 7
    ('indie'),        -- 8
    ('atmospheric'),  -- 9
    ('sci-fi'),       -- 10
    ('roguelite');    -- 11

-- =============================================================
-- Игры
-- =============================================================

-- 1. Dishonored
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Dishonored',
    '2012-10-09',
    'Стелс-экшен от первого лица в стимпанк-городе Дануолл. '
    'Игрок управляет Корво Аттано — телохранителем, ложно обвинённым в убийстве. '
    'Игра предлагает несколько путей прохождения: от скрытного до агрессивного.',
    1, 1
);

-- 2. The Witcher 3: Wild Hunt
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'The Witcher 3: Wild Hunt',
    '2015-05-19',
    'Масштабная ролевая игра в открытом мире. Ведьмак Геральт ищет свою приёмную дочь Цири '
    'в мире, раздираемом войной. Богатейший нарратив, живой открытый мир '
    'и сотни часов квестов.',
    2, 2
);

-- 3. Cyberpunk 2077
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Cyberpunk 2077',
    '2020-12-10',
    'RPG-экшен в антиутопическом мегаполисе Найт-Сити. Игрок управляет наёмником V, '
    'охотящимся за уникальным нейроимплантом с цифровым духом легендарного рокера '
    'Джонни Сильверхенда.',
    2, 2
);

-- 4. Portal 2
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Portal 2',
    '2011-04-19',
    'Головоломка от первого лица с порталами. Игрок проходит испытательные камеры, '
    'используя портальную пушку для решения пространственных задач. '
    'Блестящий кооперативный режим и незабываемый ИИ-антагонист GLaDOS.',
    3, 3
);

-- 5. Dark Souls III
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Dark Souls III',
    '2016-03-24',
    'Мрачный экшен-RPG в умирающем фэнтезийном мире. Сложный, но честный геймплей, '
    'глубокий лор и незабываемые боссы сделали серию Dark Souls культовой. '
    'Последняя часть основной трилогии.',
    4, 4
);

-- 6. Hades
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Hades',
    '2020-09-17',
    'Рогалик-экшен: сын Аида пытается сбежать из подземного царства. '
    'Каждый забег уникален, а история раскрывается через диалоги с богами Олимпа. '
    'Обладатель бесчисленных наград, включая Hugo Award.',
    5, 5
);

-- 7. Hollow Knight
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Hollow Knight',
    '2017-02-24',
    'Метроидвания в огромном подземном королевстве жуков. Исследование, сложные сражения, '
    'потрясающий рисованный арт-дизайн и меланхоличная атмосфера угасающего мира.',
    6, 6
);

-- 8. Sekiro: Shadows Die Twice
INSERT INTO games (title, release_date, description, developer_id, publisher_id)
VALUES (
    'Sekiro: Shadows Die Twice',
    '2019-03-22',
    'Экшен от третьего лица в средневековой Японии эпохи Сэнгоку. '
    'Игрок управляет ниндзя Волком. Акцент на ритмичном фехтовании и сломе стойки противника, '
    'а не на ролевой прокачке. Лауреат Game of the Year 2019.',
    4, 4
);

-- =============================================================
-- Платформы игр
-- =============================================================
INSERT INTO game_platforms (game_id, platform_id) VALUES
    (1, 1), (1, 2), (1, 3),              -- Dishonored: PC, PS4, XOne
    (2, 1), (2, 2), (2, 3),              -- Witcher 3: PC, PS4, XOne
    (3, 1), (3, 2), (3, 3), (3, 4),      -- Cyberpunk: PC, PS4, XOne, PS5
    (4, 1),                              -- Portal 2: PC
    (5, 1), (5, 2), (5, 3),              -- Dark Souls III: PC, PS4, XOne
    (6, 1), (6, 5),                      -- Hades: PC, Switch
    (7, 1), (7, 5),                      -- Hollow Knight: PC, Switch
    (8, 1), (8, 2), (8, 3);              -- Sekiro: PC, PS4, XOne

-- =============================================================
-- Жанры игр
-- =============================================================
INSERT INTO game_genres (game_id, genre_id) VALUES
    (1, 1), (1, 2),   -- Dishonored: Action, Stealth
    (2, 1), (2, 3),   -- Witcher 3: Action, RPG
    (3, 1), (3, 3),   -- Cyberpunk: Action, RPG
    (4, 4),           -- Portal 2: Puzzle
    (5, 1), (5, 3),   -- Dark Souls III: Action, RPG
    (6, 1), (6, 3),   -- Hades: Action, RPG
    (7, 1), (7, 5),   -- Hollow Knight: Action, Platformer
    (8, 1);           -- Sekiro: Action

-- =============================================================
-- Теги игр
-- =============================================================
INSERT INTO game_tags (game_id, tag_id) VALUES
    (1, 2), (1, 3), (1, 4),          -- Dishonored: story-rich, steampunk, dark
    (2, 1), (2, 2), (2, 4),          -- Witcher 3: open-world, story-rich, dark
    (3, 1), (3, 2), (3, 5),          -- Cyberpunk: open-world, story-rich, cyberpunk
    (4, 6), (4, 10),                 -- Portal 2: co-op, sci-fi
    (5, 4), (5, 7), (5, 9),          -- Dark Souls III: dark, challenging, atmospheric
    (6, 9), (6, 11),                 -- Hades: atmospheric, roguelite
    (7, 4), (7, 8), (7, 9),          -- Hollow Knight: dark, indie, atmospheric
    (8, 4), (8, 7), (8, 9);          -- Sekiro: dark, challenging, atmospheric

-- =============================================================
-- Ссылки на магазины
-- =============================================================
INSERT INTO game_store_links (game_id, store_name, url) VALUES
    (1, 'Steam', 'https://store.steampowered.com/app/205100/Dishonored/'),
    (2, 'Steam', 'https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/'),
    (3, 'Steam', 'https://store.steampowered.com/app/1091500/Cyberpunk_2077/'),
    (4, 'Steam', 'https://store.steampowered.com/app/620/Portal_2/'),
    (5, 'Steam', 'https://store.steampowered.com/app/374320/DARK_SOULS_III/'),
    (6, 'Steam', 'https://store.steampowered.com/app/1145360/Hades/'),
    (7, 'Steam', 'https://store.steampowered.com/app/367520/Hollow_Knight/'),
    (8, 'Steam', 'https://store.steampowered.com/app/814380/Sekiro_Shadows_Die_Twice/');
