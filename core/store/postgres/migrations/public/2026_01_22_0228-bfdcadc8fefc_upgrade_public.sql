BEGIN;

CREATE TABLE public.alembic_version_public (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_public_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> bfdcadc8fefc

INSERT INTO public.alembic_version_public (version_num) VALUES ('bfdcadc8fefc') RETURNING public.alembic_version_public.version_num;

COMMIT;

