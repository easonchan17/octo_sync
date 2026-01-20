BEGIN;

-- Running upgrade 802e1d974d92 -> 27a21462ead4

ALTER TABLE fbref.elo_ratings ADD COLUMN game_count INTEGER NOT NULL;

UPDATE public.alembic_version_fbref SET version_num='27a21462ead4' WHERE public.alembic_version_fbref.version_num = '802e1d974d92';

COMMIT;

