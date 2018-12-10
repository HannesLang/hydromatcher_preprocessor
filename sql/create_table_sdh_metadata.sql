-- Table: public.t_sdh_metadata

-- DROP TABLE public.t_sdh_metadata;

CREATE TABLE public.t_sdh_metadata
(
    id integer NOT NULL DEFAULT nextval('"T_DSH_Metadata_id_seq"'::regclass),
    qmax integer NOT NULL,
    shapefile_tablename character varying(50) COLLATE pg_catalog."default",
    qvol integer NOT NULL,
    CONSTRAINT "T_DSH_Metadata_pkey" PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.t_sdh_metadata
    OWNER to postgres;
COMMENT ON TABLE public.t_sdh_metadata
    IS 'Ganglinien-Metadaten';