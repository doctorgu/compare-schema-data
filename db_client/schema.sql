-- DROP TABLE schema_tables;
CREATE TABLE schema_tables (
    version TEXT NOT NULL,
    env_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    table_type TEXT NOT NULL,
    table_comment TEXT NOT NULL,
    PRIMARY KEY (version, env_name, db_name, table_name)
) STRICT;

-- DROP TABLE schema_columns;
CREATE TABLE schema_columns (
    version TEXT NOT NULL,
    env_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    ordinal_position INT NOT NULL,
    column_default TEXT NULL,
    is_nullable TEXT NOT NULL,
    data_type TEXT NOT NULL,
    character_maximum_length INT NULL,
    numeric_precision INT NULL,
    numeric_scale INT NULL,
    column_type TEXT NOT NULL,
    column_comment TEXT NOT NULL,
    PRIMARY KEY (version, env_name, db_name, table_name, column_name)
) STRICT;

-- DROP TABLE schema_indices;
CREATE TABLE schema_indices (
    version TEXT NOT NULL,
    env_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    index_name TEXT NOT NULL,
    column_name_comma TEXT NOT NULL,
    index_type TEXT NOT NULL,
    is_unique INT NOT NULL,
    PRIMARY KEY (version, env_name, db_name, table_name, index_name)
) STRICT;

-- DROP TABLE schema_references;
CREATE TABLE schema_references (
    version TEXT NOT NULL,
    env_name TEXT NOT NULL,
    db_name TEXT NOT NULL,
    constraint_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    referenced_table_name TEXT NOT NULL,
    referenced_column_name TEXT NOT NULL,
    PRIMARY KEY (version, env_name, db_name, constraint_name)
) STRICT;
CREATE UNIQUE INDEX schema_references_version_env_name_table_name_column_name ON schema_references (version, env_name, db_name, table_name, column_name);
