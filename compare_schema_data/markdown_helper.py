"""markdown helper"""

from pathlib import Path

from pydantic import BaseModel
from tabulate import tabulate

from compare_schema_data.models import (
    DataDiff,
    DataNotExists,
    HeaderAllType,
    HeaderDataDiffType,
    HeaderDataNotExistsType,
    HeaderSchemaDiffType,
    HeaderSchemaNotExistsType,
    SchemaDiff,
    SchemaNotExists,
    get_headers,
    get_values,
    type_to_compare_log,
)


def get_markdown_table[T: BaseModel](
    header: HeaderAllType,
    items: list[SchemaNotExists]
    | list[SchemaDiff]
    | list[DataNotExists]
    | list[DataDiff],
) -> str:
    """get markdown table"""

    if not items:
        return ""

    headers = get_headers(header)

    rows_list: list[list[str]] = []
    for item in items:
        values = get_values(header, item)
        rows_list.append(values)

    return tabulate(rows_list, headers=headers, tablefmt="github")


def write_markdown(
    *,
    schema_not_exists_list: dict[HeaderSchemaNotExistsType, list[SchemaNotExists]],
    schema_diff_list: dict[HeaderSchemaDiffType, list[SchemaDiff]],
    data_not_exists_list: dict[HeaderDataNotExistsType, list[DataNotExists]],
    data_diff_list: dict[HeaderDataDiffType, list[DataDiff]],
    remark: str,
    md_path_compare: Path,
    md_path_log: Path,
) -> tuple[bool, bool]:
    """write markdown"""

    lines_compare: list[str] = []
    lines_log: list[str] = []

    for items_all in [
        schema_not_exists_list,
        schema_diff_list,
        data_not_exists_list,
        data_diff_list,
    ]:
        for header, item_list in items_all.items():
            lines_cur = []
            if item_list:
                lines_cur.append(f"## {header}")
                lines_cur.append("")
                lines_cur.append(get_markdown_table(header, item_list))
                lines_cur.append("")

            if not lines_cur:
                continue

            if type_to_compare_log[header] == "compare":
                lines_compare.extend(lines_cur)
            else:
                lines_log.extend(lines_cur)

    if not lines_log and not lines_compare:
        return False, False

    headers: list[str] = []
    headers.append("# log for schema and data")
    if remark:
        headers.append("")
        headers.append(remark)
    headers.append("")

    if lines_compare:
        lines_final = headers + lines_compare
        md_path_compare.write_text("\n".join(lines_final), encoding="utf-8")

    if lines_log:
        lines_final = headers + lines_log
        md_path_log.write_text("\n".join(lines_final), encoding="utf-8")

    return bool(lines_compare), bool(lines_log)
