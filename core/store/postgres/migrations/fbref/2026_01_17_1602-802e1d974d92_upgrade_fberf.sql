BEGIN;

CREATE TABLE public.alembic_version_fbref (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fbref_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 802e1d974d92

ALTER TABLE fbref.match_results ALTER COLUMN home_gf SET NOT NULL;

ALTER TABLE fbref.match_results ALTER COLUMN away_gf SET NOT NULL;

INSERT INTO public.alembic_version_fbref (version_num) VALUES ('802e1d974d92') RETURNING public.alembic_version_fbref.version_num;

COMMIT;

