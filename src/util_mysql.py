"""util mysql"""

import re
import sqlite3
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.dialects.mysql import (
    BIGINT,
    BIT,
    LONGBLOB,
    LONGTEXT,
    MEDIUMBLOB,
    MEDIUMINT,
    MEDIUMTEXT,
    SET,
    TINYBLOB,
    TINYINT,
    TINYTEXT,
    YEAR,
)
from sqlalchemy.types import (
    BINARY,
    BLOB,
    BOOLEAN,
    CHAR,
    DATE,
    DATETIME,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    INTEGER,
    JSON,
    NUMERIC,
    REAL,
    SMALLINT,
    TEXT,
    TIME,
    TIMESTAMP,
    VARBINARY,
    VARCHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    Float,
    Integer,
    Numeric,
    String,
    Text,
)

CONFIG_PATH = str(Path(__file__).resolve().parent.parent / "config" / "config.yaml")


class SqlTypeGroup(BaseModel):
    ints: list[str] = []
    floats: list[str] = []
    chars: list[str] = []
    texts: list[str] = []
    binarys: list[str] = []
    date_times: list[str] = []
    others: list[str] = []


def get_column_type_to_data_type(column_type: str) -> str:
    """
    varchar(50) -> varchar
    decimal(10, 2) -> decimal
    enum('Y','N') -> enum
    int unsigned -> int
    """
    return re.split(r"[ \(]", column_type)[0]


def get_mysql_type_to_python_type() -> dict[str, str]:
    """return python type by MySQL type which sqlacodegen generates"""

    mapping: dict[str, str] = {
        # Numeric Types
        "tinyint": int.__name__,
        "smallint": int.__name__,
        "mediumint": int.__name__,
        "int": int.__name__,
        "integer": int.__name__,
        "bigint": int.__name__,
        "bit": int.__name__,
        "float": float.__name__,
        "double": float.__name__,
        "real": float.__name__,
        "decimal": Decimal.__name__,
        "numeric": Decimal.__name__,
        # String Types
        "char": str.__name__,
        "varchar": str.__name__,
        "tinytext": str.__name__,
        "text": str.__name__,
        "mediumtext": str.__name__,
        "longtext": str.__name__,
        # Date & Time Types
        "date": date.__name__,
        "datetime": datetime.__name__,
        "timestamp": datetime.__name__,
        "time": time.__name__,
        "year": int.__name__,
        # Binary Types
        "binary": bytes.__name__,
        "varbinary": bytes.__name__,
        "tinyblob": bytes.__name__,
        "blob": bytes.__name__,
        "mediumblob": bytes.__name__,
        "longblob": bytes.__name__,
        # Other Types
        "boolean": bool.__name__,
        "bool": bool.__name__,
        "json": dict.__name__,
        "enum": str.__name__,  # Standard sqlacodegen maps ENUM values to str
        "set": set.__name__,
    }

    return mapping


def get_sql_alchemy_type_groups() -> SqlTypeGroup:
    ints = [
        TINYINT.__name__,
        SMALLINT.__name__,
        MEDIUMINT.__name__,
        Integer.__name__,
        INTEGER.__name__,
        BigInteger.__name__,
        BIGINT.__name__,
    ]
    floats = [
        Float.__name__,
        FLOAT.__name__,
        Double.__name__,
        DOUBLE.__name__,
        DOUBLE_PRECISION.__name__,
        REAL.__name__,
        DECIMAL.__name__,
        NUMERIC.__name__,
        Numeric.__name__,
        DOUBLE_PRECISION.__name__,
    ]
    chars = [
        CHAR.__name__,
        String.__name__,
        VARCHAR.__name__,
    ]
    texts = [
        TINYTEXT.__name__,
        Text.__name__,
        TEXT.__name__,
        MEDIUMTEXT.__name__,
        LONGTEXT.__name__,
    ]
    binarys = [
        BINARY.__name__,
        VARBINARY.__name__,
        TINYBLOB.__name__,
        BLOB.__name__,
        MEDIUMBLOB.__name__,
        LONGBLOB.__name__,
    ]
    date_times = [
        Date.__name__,
        DATE.__name__,
        DateTime.__name__,
        DATETIME.__name__,
        TIMESTAMP.__name__,
    ]
    others = [
        Boolean.__name__,
        BOOLEAN.__name__,
        JSON.__name__,
        Enum.__name__,
        SET.__name__,
    ]

    return SqlTypeGroup(
        ints=ints,
        floats=floats,
        chars=chars,
        texts=texts,
        binarys=binarys,
        date_times=date_times,
        others=others,
    )


def get_mysql_type_groups() -> SqlTypeGroup:
    ints = [
        "tinyint",
        "smallint",
        "mediumint",
        "int",
        "integer",
        "bigint",
        "bit",
    ]
    floats = [
        "float",
        "double",
        "real",
        "decimal",
        "numeric",
    ]
    chars = ["char", "varchar"]
    texts = [
        "tinytexttext",
        "mediumtext",
        "longtext",
    ]
    binarys = [
        "binary",
        "varbinary",
        "tinyblob",
        "blob",
        "mediumblob",
        "longblob",
    ]
    date_times = [
        "date",
        "datetime",
        "timestamp",
        "time",
        "year",
    ]
    others = [
        "boolean",
        "bool",
        "json",
        "enum",
        "set",
    ]

    return SqlTypeGroup(
        ints=ints,
        floats=floats,
        chars=chars,
        texts=texts,
        binarys=binarys,
        date_times=date_times,
        others=others,
    )


def get_mysql_type_to_sql_alchemy_type(allow_same_group: bool) -> dict[str, list[str]]:
    """
    return SQLAlchemy type by MySQL type which sqlacodegen generates
    """

    sql_alchemy_type_groups = get_sql_alchemy_type_groups()
    int_groups = sql_alchemy_type_groups.ints
    float_groups = sql_alchemy_type_groups.floats
    char_groups = sql_alchemy_type_groups.chars
    text_groups = sql_alchemy_type_groups.texts
    binary_groups = sql_alchemy_type_groups.binarys
    date_time_groups = sql_alchemy_type_groups.date_times

    mapping: dict[str, list[str]] = {
        # Numeric Types
        "tinyint": [TINYINT.__name__] + int_groups,
        "smallint": [SMALLINT.__name__] + int_groups,
        "mediumint": [MEDIUMINT.__name__] + int_groups,
        "int": [Integer.__name__, INTEGER.__name__] + int_groups,
        "integer": [Integer.__name__, INTEGER.__name__] + int_groups,
        "bigint": [BigInteger.__name__, BIGINT.__name__] + int_groups,
        "bit": [BIT.__name__] + int_groups,
        "float": [Float.__name__, FLOAT.__name__] + float_groups,
        "double": [Double.__name__, DOUBLE.__name__, DOUBLE_PRECISION.__name__]
        + float_groups,
        "real": [REAL.__name__] + float_groups,
        "decimal": [
            DECIMAL.__name__,
            Numeric.__name__,
            NUMERIC.__name__,
            DOUBLE_PRECISION.__name__,
        ]
        + float_groups,
        "numeric": [
            Numeric.__name__,
            NUMERIC.__name__,
            DECIMAL.__name__,
            DOUBLE_PRECISION.__name__,
        ]
        + float_groups,
        # String Types
        "char": [CHAR.__name__] + char_groups,
        "varchar": [String.__name__, VARCHAR.__name__] + char_groups,
        "tinytext": [TINYTEXT.__name__] + text_groups,
        "text": [Text.__name__, TEXT.__name__] + text_groups,
        "mediumtext": [MEDIUMTEXT.__name__] + text_groups,
        "longtext": [LONGTEXT.__name__] + text_groups,
        # Binary Types
        "binary": [BINARY.__name__] + binary_groups,
        "varbinary": [VARBINARY.__name__] + binary_groups,
        "tinyblob": [TINYBLOB.__name__] + binary_groups,
        "blob": [BLOB.__name__] + binary_groups,
        "mediumblob": [MEDIUMBLOB.__name__] + binary_groups,
        "longblob": [LONGBLOB.__name__] + binary_groups,
        # Date & Time Types
        "date": [Date.__name__, DATE.__name__] + date_time_groups,
        "datetime": [DateTime.__name__, DATETIME.__name__] + date_time_groups,
        "timestamp": [TIMESTAMP.__name__] + date_time_groups,
        "time": [TIME.__name__],
        "year": [YEAR.__name__],
        # Miscellaneous
        "boolean": [Boolean.__name__, BOOLEAN.__name__],
        "bool": [Boolean.__name__, BOOLEAN.__name__],
        "json": [JSON.__name__],
        "enum": [Enum.__name__],
        "set": [SET.__name__],
    }

    return mapping


def get_sql_alchemy_types(column_type: str, allow_same_group: bool) -> list[str]:
    """return possible SQLAlchemy types"""

    map = get_mysql_type_to_sql_alchemy_type(allow_same_group)
    # varchar(50) -> varchar / 50
    # int unsigned -> int
    # double(10,0) unsigned -> double / (10,0) (ignore unsigned)
    values = column_type.replace(" unsigned", "").split("(")
    data_type = values[0]
    in_parenthesis = ""
    if len(values) == 2:
        in_parenthesis = values[1].split(")")[0]

    sql_alchemy_types = map[data_type]

    # append arguments (e.g. VARCHAR -> VARCHAR(50))
    if in_parenthesis:
        sql_alchemy_types = [f"{type}({in_parenthesis})" for type in sql_alchemy_types]
    else:
        sql_alchemy_types = [f"{type}" for type in sql_alchemy_types]

    return sql_alchemy_types


def get_data_type_is_number(data_type: str) -> bool:
    """return whether data type is number"""
    mysql_type_groups = get_mysql_type_groups()
    return data_type in mysql_type_groups.ints + mysql_type_groups.floats


def get_column_type_is_number(column_type: str) -> bool:
    """return whether column type is number"""
    data_type = get_column_type_to_data_type(column_type)
    return get_data_type_is_number(data_type)


def get_column_ddl(row: sqlite3.Row) -> str:
    """get column ddl"""

    ddl = f"{row['column_name']} {row['column_type']}"
    if row["is_nullable"] == "NO":
        ddl += " NOT NULL"
    if row["column_default"]:
        is_number = get_data_type_is_number(row["data_type"])
        quote = "'" if not is_number else ""
        ddl += f" DEFAULT {quote}{row['column_default']}{quote}"
    if row["column_comment"]:
        quote = "'"
        ddl += f" COMMENT {quote}{row['column_comment']}{quote}"
    return ddl
