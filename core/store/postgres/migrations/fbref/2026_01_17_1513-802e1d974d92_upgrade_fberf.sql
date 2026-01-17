BEGIN;

CREATE TABLE public.alembic_version_fbref (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fbref_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 802e1d974d92

DROP INDEX fbref.idx_match_fixtures_away_code;

DROP INDEX fbref.idx_match_fixtures_home_code;

CREATE INDEX idx_match_fixtures_away_code_season ON fbref.match_fixtures (away_code, season);

CREATE INDEX idx_match_fixtures_home_code_season ON fbref.match_fixtures (home_code, season);

ALTER TABLE fbref.match_results ALTER COLUMN home_gf SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN away_gf SET NOT NULL;

INSERT INTO public.alembic_version_fbref (version_num) VALUES ('802e1d974d92') RETURNING public.alembic_version_fbref.version_num;

COMMIT;

