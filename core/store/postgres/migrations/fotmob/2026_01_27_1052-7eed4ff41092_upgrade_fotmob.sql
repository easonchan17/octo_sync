BEGIN;

CREATE TABLE public.alembic_version_fotmob (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fotmob_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 86e0505f9aa6

INSERT INTO public.alembic_version_fotmob (version_num) VALUES ('86e0505f9aa6') RETURNING public.alembic_version_fotmob.version_num;

-- Running upgrade 86e0505f9aa6 -> 360f5d531f86

CREATE TABLE fotmob.daily_sync_state (
    id SERIAL NOT NULL, 
    event_date DATE NOT NULL, 
    sync_flags BIGINT NOT NULL, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (event_date)
);

CREATE INDEX idx_daily_sync_state_created_at ON fotmob.daily_sync_state (created_at);

CREATE INDEX idx_daily_sync_state_updated_at ON fotmob.daily_sync_state (updated_at);

UPDATE public.alembic_version_fotmob SET version_num='360f5d531f86' WHERE public.alembic_version_fotmob.version_num = '86e0505f9aa6';

-- Running upgrade 360f5d531f86 -> 7eed4ff41092

ALTER TABLE fotmob.daily_sync_state ADD COLUMN details JSONB;

UPDATE public.alembic_version_fotmob SET version_num='7eed4ff41092' WHERE public.alembic_version_fotmob.version_num = '360f5d531f86';

COMMIT;

