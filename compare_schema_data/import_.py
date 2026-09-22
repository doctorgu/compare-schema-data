"""compare schema between dev, stg, prd"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import cast

from mysqlclient_client.client import Client
from mysqlclient_client.settings import Settings
from pydantic_settings import BaseSettings, SettingsConfigDict

from compare_schema_data.config import CompareConfig, DataTableConfig, EnvConfig
from compare_schema_data.models import (
    DataDiff,
    DataNotExists,
    DifferentType,
    ExistsDiffType,
    HeaderAllType,
    HeaderDataDiffType,
    HeaderDataNotExistsType,
    HeaderSchemaDiffType,
    HeaderSchemaNotExistsType,
    ObjectType,
    SchemaDataType,
    SchemaDiff,
    SchemaNotExists,
)
from compare_schema_data.util_mysql import get_column_ddl
from compare_schema_data.util_path import load_config
from db_client.schema_client import SchemaClient
from db_client.schema_settings import SCHEMA_SQL_PATH, SQLITE_PATH


def get_db_settings(env: EnvConfig, db_name: str, config: CompareConfig):
    dir_queries = Path(__file__).parent.parent / "db_client" / "queries" / "source"
    return Settings(
        host=env.db_host or "",
        port=env.db_port or 0,
        database=db_name,
        user=env.db_username or "",
        password=env.db_password or "",
        dir_queries=dir_queries,
    )


def get_latest_version(db: SchemaClient) -> str:
    """get latest version"""

    row = db.read_row("read_latest_version", {})
    return row["version"] if row else ""


def delete_schema(db: SchemaClient, version: str):
    """delete schema for version"""

    db.update(
        "delete_schema_by_version",
        {
            "version": version,
        },
    )


def delete_data(db: SchemaClient, version: str, data_tables: list[DataTableConfig]):
    """delete data for version"""

    db.updates(
        [
            (
                "delete_data_by_version",
                {
                    "table": f'"{data_table.table}"',
                    "version": version,
                },
            )
            for data_table in data_tables
        ]
    )


def get_schema(
    version: str,
    config: CompareConfig,
) -> dict[str, list[dict]]:
    """get schema from mysql"""

    tables: list[dict] = []
    columns: list[dict] = []
    indices: list[dict] = []
    references: list[dict] = []

    for env in config.envs:
        # Connect to MySQL and fetch data
        for db_name in env.db_names:
            db_settings = get_db_settings(env, db_name, config)
            with Client(db_settings) as src_db:
                params = {
                    "version": version,
                    "env_name": env.name,
                    "db_name": db_name,
                }
                rows_table = src_db.read_rows("read_table", params)
                rows_column = src_db.read_rows("read_column", params)
                rows_index = src_db.read_rows("read_index", params)
                rows_reference = src_db.read_rows("read_reference", params)

                tables.extend(
                    [
                        {
                            "version": version,
                            "env_name": env.name,
                            "db_name": db_name,
                            "table_name": row["TABLE_NAME"],
                            "table_type": row["TABLE_TYPE"],
                            "table_comment": row["TABLE_COMMENT"],
                        }
                        for row in rows_table
                    ]
                )

                columns.extend(
                    [
                        {
                            "version": version,
                            "env_name": env.name,
                            "db_name": db_name,
                            "table_name": row["TABLE_NAME"],
                            "column_name": row["COLUMN_NAME"],
                            "ordinal_position": row["ORDINAL_POSITION"],
                            "column_default": row["COLUMN_DEFAULT"],
                            "is_nullable": row["IS_NULLABLE"],
                            "data_type": row["DATA_TYPE"],
                            "character_maximum_length": row["CHARACTER_MAXIMUM_LENGTH"],
                            "numeric_precision": row["NUMERIC_PRECISION"],
                            "numeric_scale": row["NUMERIC_SCALE"],
                            "column_type": row["COLUMN_TYPE"],
                            "column_comment": row["COLUMN_COMMENT"],
                        }
                        for row in rows_column
                    ]
                )

                indices.extend(
                    [
                        {
                            "version": version,
                            "env_name": env.name,
                            "db_name": db_name,
                            "table_name": row["TABLE_NAME"],
                            "index_name": row["INDEX_NAME"],
                            "column_name_comma": row["COLUMN_NAME_COMMA"],
                            "index_type": row["INDEX_TYPE"],
                            "is_unique": row["IS_UNIQUE"],
                        }
                        for row in rows_index
                    ]
                )

                references.extend(
                    [
                        {
                            "version": version,
                            "env_name": env.name,
                            "db_name": db_name,
                            "constraint_name": row["CONSTRAINT_NAME"],
                            "table_name": row["TABLE_NAME"],
                            "column_name": row["COLUMN_NAME"],
                            "referenced_table_name": row["REFERENCED_TABLE_NAME"],
                            "referenced_column_name": row["REFERENCED_COLUMN_NAME"],
                        }
                        for row in rows_reference
                    ]
                )

    return {
        "tables": tables,
        "columns": columns,
        "indices": indices,
        "references": references,
    }


def insert_schema(db: SchemaClient, schema: dict[str, list[dict]]):
    """insert schema to mysql_schema"""

    tables = schema.get("tables")
    if tables:
        db.update("insert_tables_from_mysql", tables)

    columns = schema.get("columns")
    if columns:
        db.update("insert_columns_from_mysql", columns)

    indices = schema.get("indices")
    if indices:
        db.update("insert_indices_from_mysql", indices)

    references = schema.get("references")
    if references:
        db.update("insert_references_from_mysql", references)

    print("Schema imported from MySQL")


def strip_db_obj(value: str) -> str:
    """strip double quote and backtick from db object name"""
    return value.strip('"`')


def get_data(
    version: str,
    config: CompareConfig,
) -> dict[str, list[dict]]:
    """get data from mysql"""

    data: dict[str, list[dict]] = {
        data_table.table: [] for data_table in config.data_tables
    }

    for env in config.envs:
        # Connect to MySQL and fetch data
        for db_name in env.db_names:
            db_settings = get_db_settings(env, db_name, config)
            with Client(db_settings) as src_db:
                for data_table in config.data_tables:
                    columns_list = ", ".join(
                        f"`{strip_db_obj(c)}`" for c in data_table.columns
                    )
                    key_columns_list = ", ".join(
                        f"`{strip_db_obj(k)}`" for k in data_table.key_columns
                    )
                    read_params = {
                        "version": version,
                        "env_name": env.name,
                        "db_name": db_name,
                        "table": data_table.table,
                        "columns_list": columns_list,
                        "key_columns_list": key_columns_list,
                    }
                    rows = src_db.read_rows("read_data", read_params)
                    if not rows:
                        continue

                    columns_str = ", ".join(
                        f'"{strip_db_obj(c)}"' for c in data_table.columns
                    )
                    values_str = ", ".join(
                        f":{strip_db_obj(c)}" for c in data_table.columns
                    )

                    params_list = [
                        {
                            "table": f'"{data_table.table}"',
                            "columns": columns_str,
                            "values": values_str,
                            "version": version,
                            "env_name": env.name,
                            "db_name": db_name,
                            **{
                                strip_db_obj(c): row[strip_db_obj(c)]
                                for c in data_table.columns
                            },
                        }
                        for row in rows
                    ]
                    data[data_table.table].extend(params_list)

    return data


def insert_data(db: SchemaClient, data: dict[str, list[dict]]):
    """insert data to mysql_schema"""

    for params_list in data.values():
        if params_list:
            db.update("insert_data_from_mysql", params_list)

    print("Data imported from MySQL")


def mysql_to_sqlite_type(data_type: str) -> str:
    """map mysql data type to sqlite strict data type"""
    dt = data_type.lower().split("(")[0].strip()
    if dt in {
        "int",
        "integer",
        "tinyint",
        "smallint",
        "mediumint",
        "bigint",
        "bit",
    }:
        return "INT"
    if dt in {
        "float",
        "double",
        "decimal",
        "dec",
        "numeric",
        "real",
        "double precision",
    }:
        return "REAL"
    if dt in {
        "blob",
        "tinyblob",
        "mediumblob",
        "longblob",
        "binary",
        "varbinary",
    }:
        return "BLOB"
    return "TEXT"


def create_data_table_query(
    db: SchemaClient,
    data_table: DataTableConfig,
    schema: dict[str, list[dict]],
):
    """create data table with strict option and unique index"""

    cols_schema = schema.get("columns") or []

    col_map: dict[str, dict] = {}
    for col in cols_schema:
        t_name = str(col.get("table_name", "")).lower()
        if t_name == data_table.table.lower():
            c_name = str(col.get("column_name", "")).lower()
            if (
                c_name not in col_map
                or str(col.get("is_nullable", "")).upper() == "YES"
            ):
                col_map[c_name] = col

    column_defs: list[str] = [
        '    "uid" INTEGER PRIMARY KEY AUTOINCREMENT,',
        '    "version" TEXT NOT NULL,',
        '    "env_name" TEXT NOT NULL,',
        '    "db_name" TEXT NOT NULL,',
    ]

    for c in data_table.columns:
        col_name = strip_db_obj(c)
        col_info = col_map.get(col_name.lower())

        if col_info:
            sqlite_type = mysql_to_sqlite_type(col_info.get("data_type", "text"))
            is_nullable = col_info.get("is_nullable", "YES")
            null_clause = "NOT NULL" if str(is_nullable).upper() == "NO" else "NULL"
        else:
            sqlite_type = "TEXT"
            null_clause = "NULL"

        col_id = f'"{col_name}"'
        column_defs.append(f"    {col_id} {sqlite_type} {null_clause},")

    column_defs[-1] = column_defs[-1].rstrip(",")

    key_cols = ", ".join(f'"{strip_db_obj(k)}"' for k in data_table.key_columns)
    index_cols = (
        f'"version", "env_name", "db_name", {key_cols}'
        if key_cols
        else '"version", "env_name", "db_name"'
    )

    db.update(
        "create_table_index",
        {
            "table": data_table.table,
            "columns": "\n".join(column_defs),
            "index_cols": index_cols,
        },
    )


def create_data_tables(
    db: SchemaClient,
    data_tables: list[DataTableConfig],
    schema: dict[str, list[dict]],
):
    """create or update data tables in sqlite with strict option"""

    cols_schema = schema.get("columns") or []

    for data_table in data_tables:
        col_map: dict[str, dict] = {}
        for col in cols_schema:
            t_name = str(col.get("table_name", "")).lower()
            if t_name == data_table.table.lower():
                c_name = str(col.get("column_name", "")).lower()
                if (
                    c_name not in col_map
                    or str(col.get("is_nullable", "")).upper() == "YES"
                ):
                    col_map[c_name] = col

        expected_cols: list[tuple[str, str, int]] = [
            ("uid", "INTEGER", 0),
            ("version", "TEXT", 1),
            ("env_name", "TEXT", 1),
            ("db_name", "TEXT", 1),
        ]
        for c in data_table.columns:
            col_name = strip_db_obj(c)
            col_info = col_map.get(col_name.lower())
            if col_info:
                sqlite_type = mysql_to_sqlite_type(col_info.get("data_type", "text"))
                is_nullable = col_info.get("is_nullable", "YES")
                notnull_val = 1 if str(is_nullable).upper() == "NO" else 0
            else:
                sqlite_type = "TEXT"
                notnull_val = 0
            expected_cols.append((col_name.lower(), sqlite_type.upper(), notnull_val))

        sql_row = db.read_row("read_table_sql", {"table": data_table.table})

        if not sql_row:
            create_data_table_query(db, data_table, schema)
            print(f"Created table {data_table.table}")
        else:
            table_sql = sql_row["sql"] if sql_row else ""
            is_strict = "STRICT" in table_sql.upper().split()

            rows_table_info = db.read_rows(
                "read_table_info", {"table": data_table.table}
            )
            existing_cols = [
                (r["name"].lower(), r["type"].upper(), r["notnull"])
                for r in rows_table_info
            ]

            if not is_strict or existing_cols != expected_cols:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_table = f"_back_{timestamp}_{data_table.table}"
                db.update(
                    "create_backup_table",
                    {
                        "backup_table": backup_table,
                        "table": data_table.table,
                    },
                )
                create_data_table_query(db, data_table, schema)
                print(f"Backed up {data_table.table} to {backup_table} and recreated")


def get_header_type(
    is_same_a_b: bool,
    version: str,
    current_version: str,
    schema_data: SchemaDataType,
    exists_diff: ExistsDiffType,
) -> HeaderAllType:
    """get header type"""

    if schema_data == "schema":
        if exists_diff == "exists":
            if is_same_a_b:
                if version == current_version:
                    return "schema_added"
                else:
                    return "schema_removed"
            else:
                return "schema_not_exists"
        elif exists_diff == "diff":
            if is_same_a_b:
                return "schema_changed"
            else:
                return "schema_diff"
    elif schema_data == "data":
        if exists_diff == "exists":
            if is_same_a_b:
                if version == current_version:
                    return "data_added"
                else:
                    return "data_removed"
            else:
                return "data_not_exists"
        elif exists_diff == "diff":
            if is_same_a_b:
                return "data_changed"
            else:
                return "data_diff"


def get_schema_different_value(
    *,
    rows: list[sqlite3.Row],
    env_db_a: str,
    env_db_b: str,
    version: str,
    other_version: str,
    check_column_name: bool = False,
    check_index_name: bool = False,
    check_constraint_name: bool = False,
    compare_columns: list[DifferentType],
) -> list[SchemaDiff]:
    """get different object property"""

    diff_list: list[SchemaDiff] = []
    for row in rows:
        for column in compare_columns:
            if row[f"{column}_a"] != row[f"{column}_b"]:
                table_name = row["table_name"]
                column_name = row["column_name"] if check_column_name else ""
                index_name = row["index_name"] if check_index_name else ""
                constraint_name = (
                    row["constraint_name"] if check_constraint_name else ""
                )
                different_type = column
                value_a = row[f"{column}_a"]
                value_b = row[f"{column}_b"]

                diff_list.append(
                    SchemaDiff(
                        table_name=table_name,
                        column_name=column_name,
                        index_name=index_name,
                        constraint_name=constraint_name,
                        different_type=different_type,
                        value_a=value_a,
                        value_b=value_b,
                        env_db_a=env_db_a,
                        env_db_b=env_db_b,
                        version_a=version,
                        version_b=other_version,
                    )
                )

    return diff_list


def get_filter_stmt(key_columns: list[str], row: sqlite3.Row) -> str:
    """get filter stmt"""

    stmts = [f"{strip_db_obj(k)} = '{row[strip_db_obj(k)]}'" for k in key_columns]
    return " and ".join(stmts)


def get_data_different_value(
    *,
    rows: list[sqlite3.Row],
    env_db_a: str,
    env_db_b: str,
    version: str,
    other_version: str,
    table_name: str,
    key_columns: list[str],
    compare_columns: list[str],
) -> list[DataDiff]:
    """get different column property"""

    diff_list: list[DataDiff] = []

    for row in rows:
        for column in compare_columns:
            if row[f"{column}_a"] != row[f"{column}_b"]:
                filter_stmt = get_filter_stmt(key_columns, row)
                value_a = row[f"{column}_a"]
                value_b = row[f"{column}_b"]

                diff_list.append(
                    DataDiff(
                        table_name=table_name,
                        filter_stmt=filter_stmt,
                        different_column=column,
                        value_a=value_a,
                        value_b=value_b,
                        env_db_a=env_db_a,
                        env_db_b=env_db_b,
                        version_a=version,
                        version_b=other_version,
                    )
                )

    return diff_list


def compare_schema_not_exist(
    db: SchemaClient,
    compare_types: list[ObjectType],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> dict[HeaderSchemaNotExistsType, list[SchemaNotExists]]:
    """compare schema not exist"""

    header_to_not_exists_list: dict[
        HeaderSchemaNotExistsType, list[SchemaNotExists]
    ] = {
        "schema_not_exists": [],
        "schema_added": [],
        "schema_removed": [],
    }

    for compare in config.compare_list:
        is_same_a_b = compare.a == compare.b
        if is_same_a_b:
            other_version = prev_version
            current_other_list = [
                (version, other_version, compare.a, compare.b),
                (other_version, version, compare.a, compare.b),
            ]
        else:
            current_other_list = [
                (version, "", compare.a, compare.b),
                (version, "", compare.b, compare.a),
            ]

        for current_version, other_version, current, other in current_other_list:
            current_env_name, current_db_name = current.split(".")
            other_env_name, other_db_name = other.split(".")

            header = cast(
                HeaderSchemaNotExistsType,
                get_header_type(
                    is_same_a_b, version, current_version, "schema", "exists"
                ),
            )

            if not is_same_a_b or "table" in compare_types:
                rows_table = db.read_rows(
                    "read_schema_not_exists_table",
                    {
                        "current_version": current_version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                        "exclude_tables": (
                            config.exclude_tables
                            if current_env_name != other_env_name
                            else []
                        ),
                    },
                )
                if rows_table:
                    for row in rows_table:
                        header_to_not_exists_list[header].append(
                            SchemaNotExists(
                                exists_table=row["table_name"],
                                object_type="table",
                                exists_env_db=current,
                                not_exists_env_db=other,
                                exists_version=current_version,
                                not_exists_version=other_version,
                            )
                        )

            if not is_same_a_b or "view" in compare_types:
                rows_view = db.read_rows(
                    "read_schema_not_exists_view",
                    {
                        "current_version": current_version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                    },
                )
                if rows_view:
                    for row in rows_view:
                        header_to_not_exists_list[header].append(
                            SchemaNotExists(
                                exists_table=row["view_name"],
                                object_type="view",
                                exists_env_db=current,
                                not_exists_env_db=other,
                                exists_version=current_version,
                                not_exists_version=other_version,
                            )
                        )

            if not is_same_a_b or "column" in compare_types:
                rows_column = db.read_rows(
                    "read_schema_not_exists_column",
                    {
                        "current_version": current_version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                        "exclude_tables": (
                            config.exclude_tables
                            if current_env_name != other_env_name
                            else []
                        ),
                        "exclude_columns": (
                            config.exclude_columns
                            if current_env_name != other_env_name
                            else []
                        ),
                    },
                )
                if rows_column:
                    for row in rows_column:
                        column_ddl = get_column_ddl(row)
                        header_to_not_exists_list[header].append(
                            SchemaNotExists(
                                exists_table=row["table_name"],
                                exists_column=column_ddl,
                                object_type="column",
                                exists_env_db=current,
                                not_exists_env_db=other,
                                exists_version=current_version,
                                not_exists_version=other_version,
                            )
                        )

            if not is_same_a_b or "index" in compare_types:
                rows_index = db.read_rows(
                    "read_schema_not_exists_index",
                    {
                        "current_version": current_version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                    },
                )
                if rows_index:
                    for row in rows_index:
                        header_to_not_exists_list[header].append(
                            SchemaNotExists(
                                exists_table=row["table_name"],
                                exists_index=f"{row['index_name']}({row['column_name_comma']})",
                                object_type="index",
                                exists_env_db=current,
                                not_exists_env_db=other,
                                exists_version=current_version,
                                not_exists_version=other_version,
                            )
                        )

            if not is_same_a_b or "reference" in compare_types:
                rows_reference = db.read_rows(
                    "read_schema_not_exists_reference",
                    {
                        "current_version": current_version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                    },
                )
                if rows_reference:
                    for row in rows_reference:
                        header_to_not_exists_list[header].append(
                            SchemaNotExists(
                                exists_table=row["table_name"],
                                exists_constraint=row["constraint_name"],
                                object_type="reference",
                                exists_env_db=current,
                                not_exists_env_db=other,
                                exists_version=current_version,
                                not_exists_version=other_version,
                            )
                        )

    return header_to_not_exists_list


def compare_schema_diff(
    db: SchemaClient,
    compare_types: list[ObjectType],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> dict[HeaderSchemaDiffType, list[SchemaDiff]]:
    """compare schema diff"""

    header_to_diff_list: dict[HeaderSchemaDiffType, list[SchemaDiff]] = {
        "schema_diff": [],
        "schema_changed": [],
    }

    for compare in config.compare_list:
        is_same_a_b = compare.a == compare.b
        other_version = prev_version if is_same_a_b else ""

        current, other = compare.a, compare.b
        current_env_name, current_db_name = current.split(".")
        other_env_name, other_db_name = other.split(".")

        header = cast(
            HeaderSchemaDiffType,
            get_header_type(is_same_a_b, version, other_version, "schema", "diff"),
        )

        if not is_same_a_b or "table" in compare_types:
            rows = db.read_rows(
                "read_schema_different_table",
                {
                    "current_version": version,
                    "other_version": other_version,
                    "current_env_name": current_env_name,
                    "current_db_name": current_db_name,
                    "other_env_name": other_env_name,
                    "other_db_name": other_db_name,
                    "exclude_tables": (
                        config.exclude_tables
                        if current_env_name != other_env_name
                        else []
                    ),
                },
            )
            diffs_table = get_schema_different_value(
                rows=rows,
                env_db_a=current,
                env_db_b=other,
                version=version,
                other_version=other_version,
                compare_columns=["table_type", "table_comment"],
            )
            header_to_diff_list[header].extend(diffs_table)

        if not is_same_a_b or "column" in compare_types:
            rows = db.read_rows(
                "read_schema_different_column",
                {
                    "current_version": version,
                    "other_version": other_version,
                    "current_env_name": current_env_name,
                    "current_db_name": current_db_name,
                    "other_env_name": other_env_name,
                    "other_db_name": other_db_name,
                    "exclude_tables": (
                        config.exclude_tables
                        if current_env_name != other_env_name
                        else []
                    ),
                    "exclude_columns": (
                        config.exclude_columns
                        if current_env_name != other_env_name
                        else []
                    ),
                },
            )
            diffs_column = get_schema_different_value(
                rows=rows,
                env_db_a=current,
                env_db_b=other,
                version=version,
                other_version=other_version,
                check_column_name=True,
                compare_columns=[
                    "column_default",
                    "is_nullable",
                    "data_type",
                    "character_maximum_length",
                    "numeric_precision",
                    "numeric_scale",
                    "column_comment",
                ],
            )
            header_to_diff_list[header].extend(diffs_column)

        if not is_same_a_b or "index" in compare_types:
            rows = db.read_rows(
                "read_schema_different_index",
                {
                    "current_version": version,
                    "other_version": other_version,
                    "current_env_name": current_env_name,
                    "current_db_name": current_db_name,
                    "other_env_name": other_env_name,
                    "other_db_name": other_db_name,
                },
            )
            diffs_index = get_schema_different_value(
                rows=rows,
                env_db_a=current,
                env_db_b=other,
                version=version,
                other_version=other_version,
                check_index_name=True,
                compare_columns=["column_name_comma", "index_type", "is_unique"],
            )
            header_to_diff_list[header].extend(diffs_index)

        if not is_same_a_b or "reference" in compare_types:
            rows = db.read_rows(
                "read_schema_different_reference",
                {
                    "current_version": version,
                    "other_version": other_version,
                    "current_env_name": current_env_name,
                    "current_db_name": current_db_name,
                    "other_env_name": other_env_name,
                    "other_db_name": other_db_name,
                },
            )
            diffs_reference = get_schema_different_value(
                rows=rows,
                env_db_a=current,
                env_db_b=other,
                version=version,
                other_version=other_version,
                check_constraint_name=True,
                compare_columns=[
                    "column_name",
                    "referenced_table_name",
                    "referenced_column_name",
                ],
            )
            header_to_diff_list[header].extend(diffs_reference)

    return header_to_diff_list


def compare_data_not_exist(
    db: SchemaClient,
    compare_types: list[str],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> dict[HeaderDataNotExistsType, list[DataNotExists]]:
    """compare data not exist"""

    header_to_not_exists_list: dict[HeaderDataNotExistsType, list[DataNotExists]] = {
        "data_not_exists": [],
        "data_added": [],
        "data_removed": [],
    }

    for compare in config.compare_list:
        is_same_a_b = compare.a == compare.b
        if is_same_a_b:
            other_version = prev_version
            current_other_list = [
                (version, other_version, compare.a, compare.b),
                (other_version, version, compare.a, compare.b),
            ]
        else:
            current_other_list = [
                (version, "", compare.a, compare.b),
                (version, "", compare.b, compare.a),
            ]

        for current_version, other_version, current, other in current_other_list:
            current_env_name, current_db_name = current.split(".")
            other_env_name, other_db_name = other.split(".")

            header = cast(
                HeaderDataNotExistsType,
                get_header_type(
                    is_same_a_b, version, current_version, "data", "exists"
                ),
            )

            for data_table in config.data_tables:
                if not is_same_a_b or data_table.table in compare_types:
                    key_columns_str = ", a.".join(
                        f'"{strip_db_obj(k)}"' for k in data_table.key_columns
                    )
                    key_columns_equal_str = " AND ".join(
                        f'a."{strip_db_obj(k)}" = b."{strip_db_obj(k)}"'
                        for k in data_table.key_columns
                    )
                    rows = db.read_rows(
                        "read_data_not_exists",
                        {
                            "current_version": current_version,
                            "other_version": other_version,
                            "current_env_name": current_env_name,
                            "current_db_name": current_db_name,
                            "other_env_name": other_env_name,
                            "other_db_name": other_db_name,
                            "table": f'"{strip_db_obj(data_table.table)}"',
                            "key_columns": key_columns_str,
                            "key_columns_equal": key_columns_equal_str,
                        },
                    )
                    if rows:
                        for row in rows:
                            exists_value = ".".join(
                                str(row[strip_db_obj(k)])
                                for k in data_table.key_columns
                            )
                            filter_stmt = get_filter_stmt(data_table.key_columns, row)
                            header_to_not_exists_list[header].append(
                                DataNotExists(
                                    table_name=data_table.table,
                                    filter_stmt=filter_stmt,
                                    exists_value=exists_value,
                                    exists_env_db=current,
                                    not_exists_env_db=other,
                                    exists_version=current_version,
                                    not_exists_version=other_version,
                                )
                            )

    return header_to_not_exists_list


def compare_data_diff(
    db: SchemaClient,
    compare_types: list[str],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> dict[HeaderDataDiffType, list[DataDiff]]:
    """compare data diff"""

    header_to_diff_list: dict[HeaderDataDiffType, list[DataDiff]] = {
        "data_diff": [],
        "data_changed": [],
    }

    for compare in config.compare_list:
        is_same_a_b = compare.a == compare.b
        other_version = prev_version if is_same_a_b else ""

        current, other = compare.a, compare.b
        current_env_name, current_db_name = current.split(".")
        other_env_name, other_db_name = other.split(".")

        header = cast(
            HeaderDataDiffType,
            get_header_type(is_same_a_b, version, other_version, "data", "diff"),
        )

        for data_table in config.data_tables:
            if not is_same_a_b or data_table.table in compare_types:
                key_cols = [strip_db_obj(k) for k in data_table.key_columns]
                compare_columns = [
                    strip_db_obj(c)
                    for c in data_table.columns
                    if strip_db_obj(c) not in key_cols
                ]

                key_columns_str = ", a.".join(f'"{k}"' for k in key_cols)
                key_columns_equal_str = " AND ".join(
                    f'a."{k}" = b."{k}"' for k in key_cols
                )
                other_columns_comma_a = ", ".join(
                    f'a."{c}" "{c}_a"' for c in compare_columns
                )
                other_columns_comma_b = ", ".join(
                    f'b."{c}" "{c}_b"' for c in compare_columns
                )
                other_columns_inequal = "\n                ".join(
                    f'OR COALESCE(a."{c}", "<NULL>") != COALESCE(b."{c}", "<NULL>")'
                    for c in compare_columns
                )

                rows = db.read_rows(
                    "read_data_different",
                    {
                        "current_version": version,
                        "other_version": other_version,
                        "current_env_name": current_env_name,
                        "current_db_name": current_db_name,
                        "other_env_name": other_env_name,
                        "other_db_name": other_db_name,
                        "table": f'"{strip_db_obj(data_table.table)}"',
                        "key_columns": key_columns_str,
                        "key_columns_equal": key_columns_equal_str,
                        "other_columns_comma_a": other_columns_comma_a,
                        "other_columns_comma_b": other_columns_comma_b,
                        "other_columns_inequal": other_columns_inequal,
                    },
                )
                diffs = get_data_different_value(
                    rows=rows,
                    env_db_a=current,
                    env_db_b=other,
                    version=version,
                    other_version=other_version,
                    table_name=data_table.table,
                    key_columns=data_table.key_columns,
                    compare_columns=compare_columns,
                )
                header_to_diff_list[header].extend(diffs)

    return header_to_diff_list


def get_same_schema_by_version(
    db: SchemaClient, version: str, prev_version: str
) -> tuple[bool, list[ObjectType]]:
    """
    compare schema between prev_version and version
    and return True if same
    """

    rows_compare_type = db.read_rows(
        "read_not_same_schema",
        {
            "version": version,
            "prev_version": prev_version,
        },
    )

    is_same = not rows_compare_type
    compare_types: list[ObjectType] = [row["compare_type"] for row in rows_compare_type]

    return is_same, compare_types


def get_same_data_by_version(
    db: SchemaClient,
    version: str,
    prev_version: str,
    data_tables: list[DataTableConfig],
) -> tuple[bool, list[str]]:
    """
    compare data between prev_version and version
    and return True if same
    """

    if not data_tables:
        return True, []

    rows_compare_type = db.read_rows(
        "read_not_same_data",
        {
            "version": version,
            "prev_version": prev_version,
            "data_tables": data_tables,
        },
    )

    is_same = not rows_compare_type
    compare_types: list[str] = [row["compare_type"] for row in rows_compare_type]

    return is_same, compare_types


def compare_schema(
    db: SchemaClient,
    compare_types: list[ObjectType],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> tuple[
    dict[HeaderSchemaNotExistsType, list[SchemaNotExists]],
    dict[HeaderSchemaDiffType, list[SchemaDiff]],
]:
    """compare schema between dev, stg and prd"""

    schema_not_exists_list = compare_schema_not_exist(
        db, compare_types, version, prev_version, config
    )
    schema_diff_list = compare_schema_diff(
        db, compare_types, version, prev_version, config
    )

    return (
        schema_not_exists_list,
        schema_diff_list,
    )


def compare_data(
    db: SchemaClient,
    compare_types: list[str],
    version: str,
    prev_version: str,
    config: CompareConfig,
) -> tuple[
    dict[HeaderDataNotExistsType, list[DataNotExists]],
    dict[HeaderDataDiffType, list[DataDiff]],
]:
    """compare data between dev, stg and prd"""

    data_not_exists_list = compare_data_not_exist(
        db, compare_types, version, prev_version, config
    )
    data_diff_list = compare_data_diff(db, compare_types, version, prev_version, config)

    return (
        data_not_exists_list,
        data_diff_list,
    )


def get_config(config_path: str = ""):
    if not config_path:
        config_path = "config/config.yaml"
    if os.path.exists(config_path):
        config_path = config_path
    else:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), config_path
        )
    config = load_config(config_path, CompareConfig)
    return config


def import_schema_data(
    *,
    config_path: str = "",
    version: str = "",
):
    """import schema and data"""

    config = get_config(config_path)
    version = version or datetime.now().strftime("%Y%m%d%H00")

    sqlite_path = Path(config.sqlite_path) if config.sqlite_path else SQLITE_PATH
    if not sqlite_path.exists():
        with SchemaClient(database=sqlite_path) as sqlite_db:
            schema_script = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
            sqlite_db.conn.executescript(schema_script)

    with SchemaClient(database=sqlite_path) as db:
        schema = get_schema(
            version,
            config,
        )
        data = get_data(
            version,
            config,
        )

        create_data_tables(db, config.data_tables, schema)

        delete_schema(db, version)
        delete_data(db, version, config.data_tables)

        insert_schema(db, schema)
        insert_data(db, data)


class ConfigArgs(BaseSettings):
    # Enable automatic command-line argument parsing
    model_config = SettingsConfigDict(cli_parse_args=True, cli_ignore_unknown_args=True)

    config_path: str


class ConfigArgsImport(ConfigArgs):
    version: str | None = None


def import_by_args():
    """import from source to sqlite"""

    conf = ConfigArgsImport()
    import_schema_data(config_path=conf.config_path, version=conf.version or "")
