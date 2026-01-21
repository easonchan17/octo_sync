BEGIN;

-- Running upgrade a1ab1ab757da -> b342ceb15a9f

ALTER TABLE pinnacle.pinnacle_fixtures ALTER COLUMN fixture_id DROP NOT NULL;

UPDATE public.alembic_version_pinnacle SET version_num='b342ceb15a9f' WHERE public.alembic_version_pinnacle.version_num = 'a1ab1ab757da';

COMMIT;
