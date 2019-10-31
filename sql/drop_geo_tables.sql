-- this script drops all tables in schema 'maareplus' whose name starts with 'geo_'
-- it just writes out all the statements
-- !!!! to really drop the tables: comment the RAISE NOTICE statement and uncomment the EXECUTE statement !!!!
DO
$do$
DECLARE
   _tbl text;
BEGIN
FOR _tbl  IN
    SELECT quote_ident(table_schema) || '.'
        || quote_ident(table_name)      -- escape identifier and schema-qualify!
    FROM   information_schema.tables
    WHERE  table_name LIKE 'geo_' || '%'  -- your table name prefix
    AND    table_schema = 'maareplus'     -- exclude system schemas
LOOP
  RAISE NOTICE '%',
--   EXECUTE
  'DROP TABLE ' || _tbl;
END LOOP;
END
$do$;