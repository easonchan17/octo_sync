BEGIN;

-- Running upgrade 27a21462ead4 -> c1479d1b40ce

ALTER TABLE fbref.fbref_fixtures ADD COLUMN fixture_id INTEGER;

COMMENT ON COLUMN fbref.fbref_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

ALTER TABLE fbref.fbref_fixtures ADD UNIQUE (fixture_id);

UPDATE public.alembic_version_fbref SET version_num='c1479d1b40ce' WHERE public.alembic_version_fbref.version_num = '27a21462ead4';

COMMIT;

