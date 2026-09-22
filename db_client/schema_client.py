"""schema client"""

from pathlib import Path

from sqlite3_client.client import Client

from db_client.schema_settings import get_schema_settings, schema_settings


class SchemaClient(Client):
    """schema client"""

    def __init__(self, database: str | Path | None = None):
        settings = get_schema_settings(database) if database else schema_settings
        super().__init__(db_settings=settings)


MySqlSchemaClient = SchemaClient
