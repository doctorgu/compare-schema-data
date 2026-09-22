"""compare schema between dev, stg, prd"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.compare import compare_schema_data
from src.import_ import import_schema_data


class ConfigArgs(BaseSettings):
    # Enable automatic command-line argument parsing
    model_config = SettingsConfigDict(cli_parse_args=True, cli_ignore_unknown_args=True)

    config_path: str


class ConfigArgsImport(ConfigArgs):
    version: str | None = None


class ConfigArgsCompare(ConfigArgs):
    prev_version: str | None = None
    version: str | None = None


def import_by_args():
    """import from source to sqlite"""

    conf = ConfigArgsImport()
    import_schema_data(config_path=conf.config_path, version=conf.version or "")


def compare_by_args() -> tuple[bool, bool] | None:
    """compare schema and data"""

    conf = ConfigArgsCompare()
    return compare_schema_data(
        config_path=conf.config_path,
        version=conf.version or "",
        prev_version=conf.prev_version or "",
    )
