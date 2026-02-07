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

COMMIT;

