"""excel helper"""

from pathlib import Path

from xlsxwriter.format import Format
from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet

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
)


def write_to_sheet(
    sheet: Worksheet,
    header: HeaderAllType,
    items: list[SchemaNotExists]
    | list[SchemaDiff]
    | list[DataNotExists]
    | list[DataDiff],
    header_format: Format,
):
    """write schema or data to excel sheet"""

    if not items:
        return

    headers = get_headers(header)
    for col_idx, name in enumerate(headers):
        sheet.write(0, col_idx, name, header_format)

    row_idx = 1
    for item in items:
        values = get_values(header, item)
        for col_idx, value in enumerate(values):
            sheet.write(row_idx, col_idx, value)
        row_idx += 1


def write_excel(
    *,
    schema_not_exists_list: dict[HeaderSchemaNotExistsType, list[SchemaNotExists]],
    schema_diff_list: dict[HeaderSchemaDiffType, list[SchemaDiff]],
    data_not_exists_list: dict[HeaderDataNotExistsType, list[DataNotExists]],
    data_diff_list: dict[HeaderDataDiffType, list[DataDiff]],
    xlsx_path: Path,
):
    """write excel"""

    with Workbook(str(xlsx_path)) as workbook:
        header_format = workbook.add_format({"bold": True})

        for header, item_list in schema_not_exists_list.items():
            write_to_sheet(
                workbook.add_worksheet(header),
                header,
                item_list,
                header_format,
            )
        for header, item_list in schema_diff_list.items():
            write_to_sheet(
                workbook.add_worksheet(header),
                header,
                item_list,
                header_format,
            )

        for header, item_list in data_not_exists_list.items():
            write_to_sheet(
                workbook.add_worksheet(header),
                header,
                item_list,
                header_format,
            )
        for header, item_list in data_diff_list.items():
            write_to_sheet(
                workbook.add_worksheet(header),
                header,
                item_list,
                header_format,
            )
