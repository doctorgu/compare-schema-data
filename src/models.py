"""models"""

from typing import Literal

from pydantic import BaseModel

type ObjectType = Literal["table", "view", "column", "index", "reference"]
type CompareType = ObjectType | str

type SchemaDataType = Literal["schema", "data"]
type ExistsDiffType = Literal["exists", "diff"]

type HeaderSchemaNotExistsType = Literal[
    "schema_not_exists",
    "schema_added",
    "schema_removed",
]
type HeaderSchemaDiffType = Literal["schema_diff", "schema_changed"]
type HeaderDataNotExistsType = Literal[
    "data_not_exists",
    "data_added",
    "data_removed",
]
type HeaderDataDiffType = Literal["data_diff", "data_changed"]
type HeaderAllType = Literal[
    HeaderSchemaNotExistsType,
    HeaderSchemaDiffType,
    HeaderDataNotExistsType,
    HeaderDataDiffType,
]

type CompareLogType = Literal["compare", "log"]

type_to_compare_log: dict[HeaderAllType, CompareLogType] = {
    "schema_not_exists": "compare",
    "schema_added": "log",
    "schema_removed": "log",
    "schema_diff": "compare",
    "schema_changed": "log",
    "data_not_exists": "compare",
    "data_added": "log",
    "data_removed": "log",
    "data_diff": "compare",
    "data_changed": "log",
}

type_to_headers: dict[HeaderAllType, dict[str, str]] = {
    "schema_not_exists": {
        "exists_table": "exists_table",
        "exists_column": "exists_column",
        "exists_index": "exists_index",
        "exists_constraint": "exists_constraint",
        "object_type": "object_type",
        "exists_env_db": "exists_env_db",
        "not_exists_env_db": "not_exists_env_db",
        "exists_version": "",
        "not_exists_version": "",
    },
    "schema_added": {
        "exists_table": "table_name",
        "exists_column": "column_name",
        "exists_index": "index_name",
        "exists_constraint": "constraint_name",
        "object_type": "object_type",
        "exists_env_db": "env_db",
        "not_exists_env_db": "",
        "exists_version": "version",
        "not_exists_version": "version_old",
    },
    "schema_removed": {
        "exists_table": "table_name",
        "exists_column": "column_name",
        "exists_index": "index_name",
        "exists_constraint": "constraint_name",
        "object_type": "object_type",
        "exists_env_db": "env_db",
        "not_exists_env_db": "",
        "exists_version": "version",
        "not_exists_version": "version_old",
    },
    "schema_diff": {
        "table_name": "table_name",
        "column_name": "column_name",
        "index_name": "index_name",
        "constraint_name": "constraint_name",
        "different_type": "different_type",
        "value_a": "value_a",
        "value_b": "value_b",
        "env_db_a": "env_db_a",
        "env_db_b": "env_db_b",
        "version_a": "",
        "version_b": "",
    },
    "schema_changed": {
        "table_name": "table_name",
        "column_name": "column_name",
        "index_name": "index_name",
        "constraint_name": "constraint_name",
        "different_type": "different_type",
        "value_a": "value",
        "value_b": "value_old",
        "env_db_a": "env_db",
        "env_db_b": "",
        "version_a": "version",
        "version_b": "version_old",
    },
    "data_not_exists": {
        "table_name": "table_name",
        "filter_stmt": "filter_stmt",
        "exists_value": "exists_value",
        "exists_env_db": "exists_env_db",
        "not_exists_env_db": "not_exists_env_db",
        "exists_version": "",
        "not_exists_version": "",
    },
    "data_added": {
        "table_name": "table_name",
        "filter_stmt": "filter_stmt",
        "exists_value": "value",
        "exists_env_db": "env_db",
        "not_exists_env_db": "",
        "exists_version": "version",
        "not_exists_version": "version_old",
    },
    "data_removed": {
        "table_name": "table_name",
        "filter_stmt": "filter_stmt",
        "exists_value": "value",
        "exists_env_db": "env_db",
        "not_exists_env_db": "",
        "exists_version": "version",
        "not_exists_version": "version_old",
    },
    "data_diff": {
        "table_name": "table_name",
        "filter_stmt": "filter_stmt",
        "different_column": "different_column",
        "value_a": "value_a",
        "value_b": "value_b",
        "env_db_a": "env_db_a",
        "env_db_b": "env_db_b",
        "version_a": "",
        "version_b": "",
    },
    "data_changed": {
        "table_name": "table_name",
        "filter_stmt": "filter_stmt",
        "different_column": "different_column",
        "value_a": "value",
        "value_b": "value_old",
        "env_db_a": "env_db",
        "env_db_b": "",
        "version_a": "version",
        "version_b": "version_old",
    },
}


class SchemaNotExists(BaseModel):
    """schema not exists"""

    exists_table: str
    exists_column: str = ""
    exists_index: str = ""
    exists_constraint: str = ""
    object_type: ObjectType
    exists_env_db: str
    not_exists_env_db: str
    exists_version: str
    not_exists_version: str


type DifferentType = Literal[
    "table_type",
    "table_comment",
    "column_default",
    "is_nullable",
    "data_type",
    "character_maximum_length",
    "numeric_precision",
    "numeric_scale",
    "column_comment",
    "column_name",
    "column_name_comma",
    "index_type",
    "is_unique",
    "referenced_table_name",
    "referenced_column_name",
]


class SchemaDiff(BaseModel):
    """schema diff"""

    table_name: str
    column_name: str = ""
    index_name: str = ""
    constraint_name: str = ""
    different_type: DifferentType
    value_a: str | int
    value_b: str | int
    env_db_a: str
    env_db_b: str
    version_a: str
    version_b: str


class DataBase(BaseModel):
    """data base"""

    table_name: str
    filter_stmt: str


class DataNotExists(DataBase):
    """data not exists"""

    exists_value: str
    exists_env_db: str
    not_exists_env_db: str
    exists_version: str
    not_exists_version: str


class DataDiff(DataBase):
    """data diff"""

    different_column: str
    value_a: str | int
    value_b: str | int
    env_db_a: str
    env_db_b: str
    version_a: str
    version_b: str


def get_headers(header: HeaderAllType) -> list[str]:
    name_to_header = type_to_headers[header]
    return [value for value in name_to_header.values() if value]


def get_values(
    header: HeaderAllType,
    item: SchemaNotExists | SchemaDiff | DataNotExists | DataDiff,
) -> list[str]:
    name_to_header: dict[str, str] = type_to_headers[header]

    values: list[str] = []
    for name in type_to_headers[header].keys():
        if not name_to_header[name]:
            continue
        value = getattr(item, name, "")
        values.append(str(value))
    return values
