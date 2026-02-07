BEGIN;

CREATE TABLE public.alembic_version_fbref (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fbref_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 802e1d974d92

ALTER TABLE fbref.match_results ALTER COLUMN home_gf SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN away_gf SET NOT NULL;

INSERT INTO public.alembic_version_fbref (version_num) VALUES ('802e1d974d92') RETURNING public.alembic_version_fbref.version_num;

-- Running upgrade 802e1d974d92 -> 27a21462ead4

ALTER TABLE fbref.elo_ratings ADD COLUMN game_count INTEGER NOT NULL;

UPDATE public.alembic_version_fbref SET version_num='27a21462ead4' WHERE public.alembic_version_fbref.version_num = '802e1d974d92';

-- Running upgrade 27a21462ead4 -> c1479d1b40ce

ALTER TABLE fbref.fbref_fixtures ADD COLUMN fixture_id INTEGER;

COMMENT ON COLUMN fbref.fbref_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

ALTER TABLE fbref.fbref_fixtures ADD UNIQUE (fixture_id);

UPDATE public.alembic_version_fbref SET version_num='c1479d1b40ce' WHERE public.alembic_version_fbref.version_num = '27a21462ead4';

-- Running upgrade c1479d1b40ce -> e8747c4304df

UPDATE public.alembic_version_fbref SET version_num='e8747c4304df' WHERE public.alembic_version_fbref.version_num = 'c1479d1b40ce';

COMMIT;

