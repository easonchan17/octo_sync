BEGIN;

CREATE TABLE public.alembic_version_pinnacle (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pinnacle_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a1ab1ab757da

COMMENT ON COLUMN pinnacle.pinnacle_fixtures.fixture_id IS 'References fotmob_fixtures.match_id';

INSERT INTO public.alembic_version_pinnacle (version_num) VALUES ('a1ab1ab757da') RETURNING public.alembic_version_pinnacle.version_num;

-- Running upgrade a1ab1ab757da -> b342ceb15a9f

ALTER TABLE pinnacle.pinnacle_fixtures ALTER COLUMN fixture_id DROP NOT NULL;

UPDATE public.alembic_version_pinnacle SET version_num='b342ceb15a9f' WHERE public.alembic_version_pinnacle.version_num = 'a1ab1ab757da';

-- Running upgrade b342ceb15a9f -> 631bb64eed57

UPDATE public.alembic_version_pinnacle SET version_num='631bb64eed57' WHERE public.alembic_version_pinnacle.version_num = 'b342ceb15a9f';

COMMIT;

