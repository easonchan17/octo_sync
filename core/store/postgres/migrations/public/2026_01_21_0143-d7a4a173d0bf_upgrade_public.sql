BEGIN;

CREATE TABLE public.alembic_version_public (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_public_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> d7a4a173d0bf

DROP INDEX idx_training_records_create_at;

DROP INDEX idx_training_records_update_at;

CREATE INDEX idx_training_records_created_at ON public.training_records (created_at);

CREATE INDEX idx_training_records_updated_at ON public.training_records (updated_at);

INSERT INTO public.alembic_version_public (version_num) VALUES ('d7a4a173d0bf') RETURNING public.alembic_version_public.version_num;

COMMIT;

