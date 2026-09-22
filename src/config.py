"""config"""

import os
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    ConfigDict,
    PrivateAttr,
    field_validator,
    model_validator,
)

from db_client.schema_settings import SQLITE_PATH

load_dotenv()


def resolve_env_var(v: Any) -> Any:
    if isinstance(v, str) and v.startswith("env."):
        env_name = v.removeprefix("env.").strip()
        val = os.getenv(env_name)
        if val is None:
            val = os.getenv(env_name.upper())
        if val is None:
            val = os.getenv(env_name.lower())
        return val if val is not None else ""
    return v


class EnvConfig(BaseModel):
    name: str
    db_names: list[str]
    db_host: str | None = None
    db_port: int | None = None
    db_username: str | None = None
    db_password: str | None = None
    _parent: Any = PrivateAttr(default=None)

    @field_validator("db_host", "db_port", "db_username", "db_password", mode="before")
    @classmethod
    def resolve_env(cls, v: Any) -> Any:
        return resolve_env_var(v)

    @property
    def parent(self) -> Any:
        return self._parent

    def __getattribute__(self, name: str):
        val = super().__getattribute__(name)
        if val is None and name in {"db_host", "db_port", "db_username", "db_password"}:
            private = object.__getattribute__(self, "__pydantic_private__")
            if private:
                parent = private.get("_parent")
                if parent is not None:
                    return getattr(parent, name, None)
        return val


class EnvCompareConfig(BaseModel):
    a: str
    b: str


class DataTableConfig(BaseModel):
    table: str
    columns: list[str]
    key_columns: list[str]


class CompareConfig(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    # Report output format ("xlsx" for Excel, "md" for Markdown)
    output_type: Literal["xlsx", "md"]
    # Directory path to save output reports
    output_dir: str
    # Directory path to store SQLite database (schema_data.sqlite3)
    sqlite_path: str = str(SQLITE_PATH)

    # Configurations for tables and columns to compare data
    data_tables: list[DataTableConfig] = []

    # Tables to exclude from comparison between different environments
    exclude_tables: list[str]
    # Columns to exclude from comparison between different environments
    exclude_columns: list[str]

    # Host IP or hostname for MySQL database connections
    db_host: str
    db_port: int
    db_username: str
    db_password: str

    # Database environment connection configurations (dev, stg, prd)
    envs: list[EnvConfig]
    # List of database pairs to compare (e.g., dev.shop vs stg.shop)
    compare_list: list[EnvCompareConfig]

    @field_validator("db_host", "db_port", "db_username", "db_password", mode="before")
    @classmethod
    def resolve_env(cls, v: Any) -> Any:
        return resolve_env_var(v)

    @model_validator(mode="after")
    def inherit_parent_values(self) -> "CompareConfig":
        for env in self.envs:
            env._parent = self
            if env.__dict__.get("db_host") is None:
                env.db_host = self.db_host
            if env.__dict__.get("db_port") is None:
                env.db_port = self.db_port
            if env.__dict__.get("db_username") is None:
                env.db_username = self.db_username
            if env.__dict__.get("db_password") is None:
                env.db_password = self.db_password
        return self
