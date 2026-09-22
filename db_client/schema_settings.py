"""schema settings"""

from pathlib import Path

from sqlite3_client.settings import Settings

SQLITE_PATH = Path(__file__).resolve().parent / "schema_data.sqlite3"
SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_schema_settings(sqlite_path: str | Path = SQLITE_PATH) -> Settings:
    """get schema settings with specified sqlite file"""
    return Settings(
        database=str(sqlite_path),
        minconn=3,
        maxconn=10,
        connect_timeout=5,
        use_en_ko_column_alias=True,
        dir_queries=Path(__file__).parent / "queries" / "schema",
        before_read_execute=lambda qry_key, params, qry_str, qry_with_value: print(
            f'READ_ROWS_START, QRY_KEY: "{qry_key}", QRY_WITH_VALUE: {qry_with_value}'
        ),
        # after_read_execute=lambda qry_key, duration: print(
        #     f'READ_ROWS_END, QRY_KEY: "{qry_key}", DURATION: {duration}'
        # ),
        before_update_execute=(
            lambda qry_key, params, params_out, qry_str, qry_with_value: print(
                f'UPDATES_START, QRY_KEY: "{qry_key}", QRY_WITH_VALUE: {qry_with_value}'
            )
        ),
        # after_update_execute=lambda qry_key, row_count, params_out, duration: print(
        #     f'UPDATES_END, QRY_KEY: "{qry_key}"' f", DURATION: {duration}"
        # ),
    )


schema_settings = get_schema_settings()

mysql_schema_settings = schema_settings
