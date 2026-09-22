# compare-schema-data

[English](README.md) | [한국어](README_KO.md)

`compare-schema-data` is a database comparison and change-tracking tool built with Python. It extracts MySQL database schemas (tables, columns, indexes, foreign keys, views) and selected reference data, caches them into a local SQLite database, and generates detailed diff and audit reports in **Markdown** or **Excel** formats.

It supports two primary workflows:
1. **Cross-Environment Comparison (`compare`)**: Compare schema and data between different environments (e.g., `dev` vs `stg`, `stg` vs `prd`) at a given version.
2. **Version History & Audit Log (`log`)**: Compare snapshots between versions within the same environment (e.g., `prev_version` vs `version`) to track what was added, removed, or changed over time.

---

## Key Features

- **Comprehensive Schema Inspection**:
  - **Tables & Views**: Table types (`BASE TABLE`, `VIEW`) and table comments.
  - **Columns**: Data types, column types, lengths, precision, scale, nullability, default values, comments, and ordinal positions.
  - **Indexes**: Composite column order, index types (BTREE, etc.), uniqueness (`IS_UNIQUE`), automatically excluding foreign key generated indexes.
  - **Foreign Key Constraints**: Constraint names, source columns, referenced tables, and referenced columns.
- **Selective Data Comparison**:
  - Compare reference/master data (e.g., common codes, menu items, status definitions).
  - Automatically creates SQLite tables in `STRICT` mode, mapping MySQL data types to SQLite strict types.
  - Automatically handles SQLite schema migrations and backup (`_back_<timestamp>_<table>`).
  - Identifies missing rows (`data_not_exists`, `data_added`, `data_removed`) based on primary/composite keys, and field-level diffs (`data_diff`, `data_changed`).
- **Two-Stage SQLite Snapshot Architecture**:
  - Extracts metadata from MySQL `INFORMATION_SCHEMA` and stores it offline in SQLite (`schema_data.sqlite3`).
  - Fast execution and zero ongoing load or lock contention on live production databases during comparison.
- **Environment & Column Exclusions**:
  - Exclude migration tables (e.g., `alembic_version`) or environment-specific columns from cross-environment comparison without losing them in version logs.
- **Dual Output Formats**:
  - **Markdown (`.md`)**: GitHub-flavored markdown tables separated into `<version>_compare.md` and `<version>_log.md`.
  - **Excel (`.xlsx`)**: Multi-worksheet workbook `<version>_compare_log.xlsx` with bold headers for each diff category.
- **Secure Configuration**:
  - Seamlessly resolve passwords and usernames from `.env` or system environment variables using the `env.<VAR_NAME>` syntax.

---

## Architecture & How It Works

```text
+-------------------+      +-------------------+      +-------------------+
|     dev MySQL     |      |     stg MySQL     |      |     prd MySQL     |
+---------+---------+      +---------+---------+      +---------+---------+
          |                          |                          |
          +--------------------------+--------------------------+
                                     |
                               [ 1. import ]
                                     |
                                     v
                       +---------------------------+
                       |   schema_data.sqlite3     |
                       |  (schema & data snapshot) |
                       +-------------+-------------+
                                     |
                              [ 2. compare ]
                                     |
                                     v
                   +-----------------+-----------------+
                   |                                   |
         (Cross-Environment)                    (Version History)
        a != b (e.g. dev vs stg)              a == b (dev vs dev)
                   |                                   |
                   v                                   v
          *_compare.md / .xlsx                 *_log.md / .xlsx
      (schema_not_exists, diff, etc.)     (schema_added, changed, etc.)
```

1. **`import` step**: Queries `INFORMATION_SCHEMA.TABLES`, `COLUMNS`, `STATISTICS`, `KEY_COLUMN_USAGE`, and target `data_tables` from configured MySQL instances. Inserts them into `schema_tables`, `schema_columns`, `schema_indices`, `schema_references`, and target data tables in SQLite tagged with `version`, `env_name`, and `db_name`.
2. **`compare` step**: Runs high-performance SQL difference queries inside SQLite.
   - For pairs where `a != b` (e.g., `dev.lms` vs `stg.lms`): Generates an **environment comparison report** (`*_compare.md`).
   - For pairs where `a == b` (e.g., `dev.lms` vs `dev.lms`): Compares `version` against `prev_version` and generates a **version history log** (`*_log.md`).

---

## Requirements

- Python >= 3.13
- MySQL 5.7+ / 8.0+
- [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

---

## Installation

### Using `uv` (Recommended)

```bash
# Clone the repository
git clone https://github.com/doctorgu/compare-schema-data.git
cd compare-schema-data

# Create virtual environment and activate
uv venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies in editable mode
uv pip install -e . --native-tls
```

### Using standard `pip`

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

---

## Configuration

Configuration is managed via a YAML file (e.g., `config/config.yaml`) and an optional `.env` file for credentials.

### 1. `.env` File Setup

Create a `.env` file in your root directory (refer to `.env.example`):

```env
DB_USERNAME=your_database_username
DB_PASSWORD=your_database_password
```

### 2. `config.yaml` Structure

```yaml
# Output format: "md" for Markdown, "xlsx" for Excel
output_type: md
# Directory to store output reports
output_dir: ./data
# SQLite database path for cached metadata
sqlite_path: ./db_client/schema_data.sqlite3

# Tables and columns to compare table data
data_tables:
  - table: menu
    columns:
      - menu_code
      - upper_menu_code
      - menu_name
      - menu_url
      - is_delete
      - "order"
    key_columns:
      - menu_code
  - table: common_code
    columns:
      - group_code
      - code
      - code_name
      - code_description
      - "order"
      - is_use
    key_columns:
      - group_code
      - code

# Exclusions for cross-environment comparisons
exclude_tables: ["alembic_version"]
exclude_columns: []

# Default connection settings (supports env.<KEY> syntax)
db_host: 127.0.0.1
db_port: 3306
db_username: env.DB_USERNAME
db_password: env.DB_PASSWORD

# Environment connection specifications
# (inherits db_host, db_username, db_password from parent if omitted)
envs:
  - name: dev
    db_names: [lms, lms_next]
    db_port: 4001
  - name: stg
    db_names: [lms]
    db_port: 4004
  - name: prd
    db_names: [lms]
    db_port: 4002

# Comparison targets
compare_list:
  # Cross-environment comparisons (generates *_compare report)
  - a: dev.lms
    b: dev.lms_next
  - a: dev.lms
    b: stg.lms
  - a: stg.lms
    b: prd.lms

  # Self-comparisons (generates *_log report between versions)
  - a: dev.lms
    b: dev.lms
  - a: stg.lms
    b: stg.lms
  - a: prd.lms
    b: prd.lms
```

---

## Usage

### Step 1: Import Schema and Data (`import`)

Connects to all configured MySQL environments and imports schemas and target data into SQLite.

```bash
# Basic run (version defaults to current timestamp: YYYYMMDDHH00)
import --config_path config/config.yaml

# Run with explicit version tag
import --config_path config/config.yaml --version 202609221530
```

Alternatively, call directly in Python (`.py`):

```python
from compare_schema_data.import_ import import_schema_data

import_schema_data(config_path="config/config.yaml")
# Or specify a custom version tag:
# import_schema_data(config_path="config/config.yaml", version="202609221530")
```

### Step 2: Compare Schema and Data (`compare`)

Compares environments and version histories cached in SQLite and writes reports to `output_dir`.

```bash
# Compare the latest version with the immediately preceding version
compare --config_path config/config.yaml

# Compare specific versions
compare --config_path config/config.yaml --version 202609221530 --prev_version 202609211600
```

Alternatively, call directly in Python (`.py`):

```python
from compare_schema_data.compare import compare_schema_data

is_compare_changed, is_log_changed = compare_schema_data(
    config_path="config/config.yaml"
)
# Or specify custom versions:
# is_compare_changed, is_log_changed = compare_schema_data(
#     config_path="config/config.yaml", version="202609221530", prev_version="202609211600"
# )
```

### Complete Python Integration Example (`main.py`)

You can integrate both `import_schema_data` and `compare_schema_data` into your automation pipelines (e.g., CI/CD, scheduled jobs, alerting on change):

```python
import traceback
from pathlib import Path

from compare_schema_data.compare import compare_schema_data
from compare_schema_data.import_ import import_schema_data

from env_config import env_config
from util_other import send_discord_message


def main():
    try:
        config_path = str(Path(__file__).parent / "config.yml")
        import_schema_data(config_path=config_path)
        is_compare_changed, is_log_changed = compare_schema_data(
            config_path=config_path
        )
        if is_log_changed:
            send_discord_message(
                env_config.DISCORD_WEB_HOOK_URL, "schema or data changed"
            )
    except Exception as e:
        print(traceback.format_exc())

        send_discord_message(env_config.DISCORD_WEB_HOOK_URL, str(e))


main()
```

---

## Report Types & Output Structure

Depending on `output_type`, reports are generated in `output_dir`:

### 1. Markdown Reports (`output_type: md`)

Two files are created when differences exist:

#### A. Environment Comparison (`<version>_compare.md`)
Contains sections comparing different environments at the same version:
- `## schema_not_exists`: Objects (tables, views, columns, indexes, foreign keys) present in one environment but missing in another.
- `## schema_diff`: Schema property mismatches (defaults, nullability, data types, comments, length/precision).
- `## data_not_exists`: Rows missing in one environment based on `key_columns`.
- `## data_diff`: Column value differences for matching rows.

*Sample `schema_diff` output:*

| table_name | column_name | index_name | constraint_name | different_type | value_a | value_b | env_db_a | env_db_b |
|---|---|---|---|---|---|---|---|---|
| order | is_user_dismissed | | | is_nullable | NO | YES | dev.lms | dev.lms_next |
| textbook_classification | classification_en | | | is_nullable | YES | NO | dev.lms | dev.lms_next |

#### B. Version Audit Log (`<version>_log.md`)
Contains sections comparing the current version with `prev_version` for identical environments:
- `## schema_added`: New tables, columns, indexes, constraints added in `version`.
- `## schema_removed`: Objects deleted since `prev_version`.
- `## schema_changed`: Schema property modifications over time.
- `## data_added`: New rows inserted.
- `## data_removed`: Rows deleted.
- `## data_changed`: Values modified between versions.

*Sample `schema_added` output:*

| table_name | column_name | index_name | constraint_name | object_type | env_db | version | version_old |
|---|---|---|---|---|---|---|---|
| leveltest_product_policy | | | | table | dev.lms | 202609221530 | 202609211600 |
| leveltest_product_policy | policy_code varchar(20) NOT NULL COMMENT '정책코드' | | | column | dev.lms | 202609221530 | 202609211600 |

### 2. Excel Reports (`output_type: xlsx`)

A consolidated Excel file `<version>_compare_log.xlsx` is created containing a worksheet for each category that has differences, styled with bold headers.

---

## Project Structure

```text
compare-schema-data/
├── .env.example                     # Sample environment variable template
├── pyproject.toml                   # Project metadata, dependencies, and CLI entry points
├── README.md                        # English documentation
├── README_KO.md                     # Korean documentation
├── config/
│   ├── config.yaml                  # Full schema and data comparison configuration
│   └── config_data.yaml             # Minimal sample data comparison configuration
├── data/                            # Generated diff reports (*_compare.md, *_log.md, *.xlsx)
├── db_client/
│   ├── schema.sql                   # SQLite schema for caching metadata
│   ├── schema_settings.py           # SQLite connection settings and hooks
│   ├── schema_client.py             # SQLite client wrapper
│   ├── schema_data.sqlite3          # SQLite database storage
│   └── queries/
│       ├── schema/                  # SQLite queries for diffs & checks
│       │   ├── schema.yml
│       │   └── data.yml
│       └── source/                  # MySQL queries for metadata extraction
│           ├── import_schema.yml
│           └── import_data.yml
└── compare_schema_data/
    ├── import_.py                   # MySQL extraction, SQLite import logic, and import_by_args CLI
    ├── compare.py                   # Schema & data diff engine, and compare_by_args CLI
    ├── config.py                    # Pydantic configuration models and env resolver
    ├── models.py                    # Data models, diff types, and table header definitions
    ├── excel_helper.py              # Excel workbook generator (XlsxWriter)
    ├── markdown_helper.py           # Markdown table generator (tabulate)
    ├── util_mysql.py                # MySQL data type mappings and DDL generation
    └── util_path.py                 # File path and YAML loading utilities
```

---

## Development & Code Quality

Code formatting and linting are configured with [ruff](https://github.com/astral-sh/ruff):

```bash
# Run linter
ruff check .

# Run formatter
ruff format .
```

---

## License

This project is licensed under the [MIT License](LICENSE).

## Author

- **Gu Park** - [doctorgu@kakao.com](mailto:doctorgu@kakao.com) - [GitHub](https://github.com/doctorgu)
