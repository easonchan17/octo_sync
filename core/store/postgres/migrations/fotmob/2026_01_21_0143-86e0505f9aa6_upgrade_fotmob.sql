BEGIN;

CREATE TABLE public.alembic_version_fotmob (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_fotmob_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 86e0505f9aa6

INSERT INTO public.alembic_version_fotmob (version_num) VALUES ('86e0505f9aa6') RETURNING public.alembic_version_fotmob.version_num;

COMMIT;

