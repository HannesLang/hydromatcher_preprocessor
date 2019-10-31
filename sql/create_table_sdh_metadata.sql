-- DROP SEQUENCE maareplus.t_sdh_metadata_id_seq;
CREATE SEQUENCE maareplus.t_sdh_metadata_id_seq;

ALTER SEQUENCE maareplus.t_sdh_metadata_id_seq
    OWNER TO jlang;

-- DROP SEQUENCE maareplus.t_floodplain_id_seq;
CREATE SEQUENCE maareplus.t_floodplain_id_seq;
ALTER SEQUENCE maareplus.t_floodplain_id_seq
    OWNER TO jlang;


-- DROP TABLE maareplus.t_floodplain
CREATE TABLE maareplus.t_floodplain
(
    id integer NOT NULL DEFAULT nextval('maareplus.t_floodplain_id_seq'::regclass),
    floodplain_name character varying COLLATE pg_catalog."default" NOT NULL,
    floodplain_type character varying COLLATE pg_catalog."default" NOT NULL,
	CONSTRAINT t_floodplain_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;


-- DROP TABLE maareplus.t_sdh_metadata;
CREATE TABLE maareplus.t_sdh_metadata
(
    id integer NOT NULL DEFAULT nextval('maareplus.t_sdh_metadata_id_seq'::regclass),
    qmax integer NOT NULL,
    shapefile_tablename character varying COLLATE pg_catalog."default" NOT NULL,
    qvol integer,
    floodplain_id integer NOT NULL REFERENCES maareplus.t_floodplain(id),
    CONSTRAINT t_sdh_metadata_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE maareplus.t_sdh_metadata
    OWNER to jlang;

-- Set this to whatever ROLE (Username) is used; The search_path defines the order of schemas, in which tables are created/searched, if no schema is defined in the sql statement.
ALTER ROLE jlang SET search_path = maareplus,public;

commit;