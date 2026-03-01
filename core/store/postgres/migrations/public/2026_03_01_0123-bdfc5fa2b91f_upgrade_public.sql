BEGIN;

CREATE TABLE public.alembic_version_public (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_public_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> bfdcadc8fefc

INSERT INTO public.alembic_version_public (version_num) VALUES ('bfdcadc8fefc') RETURNING public.alembic_version_public.version_num;

-- Running upgrade bfdcadc8fefc -> 96c9b51dea64

CREATE TABLE public.leagues (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    is_popular BOOLEAN NOT NULL, 
    priority INTEGER NOT NULL, 
    sites JSONB, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE INDEX idx_leagues_created_at ON public.leagues (created_at);

CREATE INDEX idx_leagues_priority ON public.leagues (priority);

CREATE INDEX idx_leagues_updated_at ON public.leagues (updated_at);

UPDATE public.alembic_version_public SET version_num='96c9b51dea64' WHERE public.alembic_version_public.version_num = 'bfdcadc8fefc';

-- Running upgrade 96c9b51dea64 -> 2fb09c1c18a5

UPDATE public.alembic_version_public SET version_num='2fb09c1c18a5' WHERE public.alembic_version_public.version_num = '96c9b51dea64';

-- Running upgrade 2fb09c1c18a5 -> 3bb1c8095db5

CREATE TABLE public.site_leagues (
    id SERIAL NOT NULL, 
    site_name VARCHAR(100) NOT NULL, 
    league_id VARCHAR(100) NOT NULL, 
    league_name VARCHAR(200), 
    extra_data JSONB, 
    ref_league_id BIGINT, 
    status INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id), 
    CONSTRAINT uq_site_league_league_id_site UNIQUE (ref_league_id, site_name), 
    CONSTRAINT uq_site_league_site_code UNIQUE (site_name, league_id)
);

CREATE INDEX idx_site_leagues_created_at ON public.site_leagues (created_at);

CREATE INDEX idx_site_leagues_updated_at ON public.site_leagues (updated_at);

ALTER TABLE leagues ALTER COLUMN id TYPE BIGINT;

ALTER TABLE leagues ALTER COLUMN name TYPE VARCHAR(200);

ALTER TABLE leagues ALTER COLUMN priority DROP NOT NULL;

ALTER TABLE leagues DROP COLUMN is_popular;

ALTER TABLE leagues DROP COLUMN sites;

ALTER TABLE sites ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE sites ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE sites ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE sites ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE training_records ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE training_records ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE training_records ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE training_records ALTER COLUMN updated_at SET NOT NULL;

UPDATE public.alembic_version_public SET version_num='3bb1c8095db5' WHERE public.alembic_version_public.version_num = '2fb09c1c18a5';

-- Running upgrade 3bb1c8095db5 -> fb416b7aae65

ALTER TABLE leagues ADD COLUMN country_code VARCHAR(3);

ALTER TABLE leagues ADD COLUMN country_name VARCHAR(100);

ALTER TABLE leagues DROP CONSTRAINT leagues_name_key;

ALTER TABLE site_leagues ADD COLUMN country_code VARCHAR(3);

ALTER TABLE site_leagues ADD COLUMN country_name VARCHAR(100);

ALTER TABLE site_leagues ALTER COLUMN league_name SET NOT NULL;

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE public.alembic_version_public SET version_num='fb416b7aae65' WHERE public.alembic_version_public.version_num = '3bb1c8095db5';

-- Running upgrade fb416b7aae65 -> bdfc5fa2b91f

ALTER TABLE site_leagues DROP CONSTRAINT site_leagues_ref_league_id_fkey;

ALTER TABLE public.site_leagues ADD FOREIGN KEY(ref_league_id) REFERENCES public.leagues (id);

UPDATE public.alembic_version_public SET version_num='bdfc5fa2b91f' WHERE public.alembic_version_public.version_num = 'fb416b7aae65';

COMMIT;

