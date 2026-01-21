BEGIN;

CREATE TABLE public.alembic_version_pinnacle (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pinnacle_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a1ab1ab757da

COMMENT ON COLUMN pinnacle.pinnacle_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

INSERT INTO public.alembic_version_pinnacle (version_num) VALUES ('a1ab1ab757da') RETURNING public.alembic_version_pinnacle.version_num;

COMMIT;

