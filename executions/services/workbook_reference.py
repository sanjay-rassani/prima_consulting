from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from django.conf import settings

from .csv_contract import CALCULATION_SHEET, INPUT_ASSUMPTIONS_SHEET, LOOKUP_PROBABILITY_SHEET

XML_NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass(frozen=True)
class WorkbookAssumptions:
    valuation_date: date
    discount_rate: Decimal
    salary_increase_rate: Decimal
    retirement_age: int


@dataclass(frozen=True)
class ProbabilityTableEntry:
    age: int
    qx: Decimal
    px: Decimal


@dataclass(frozen=True)
class WorkbookReferenceData:
    assumptions: WorkbookAssumptions
    probability_by_age: dict[int, ProbabilityTableEntry]


@dataclass(frozen=True)
class WorkbookProjectionRow:
    age: int
    future_salary: Decimal
    survival_probability: Decimal
    death_probability: Decimal
    expected_death_outflow: Decimal


@lru_cache(maxsize=1)
def load_workbook_reference_data():
    workbook_path = Path(settings.BASE_DIR) / "sample cashflow model.xlsx"
    shared_strings, sheets = _read_workbook_sheets(workbook_path)

    assumptions_rows = _extract_sheet_rows(
        sheets[INPUT_ASSUMPTIONS_SHEET],
        shared_strings,
    )
    probability_rows = _extract_sheet_rows(
        sheets[LOOKUP_PROBABILITY_SHEET],
        shared_strings,
    )

    assumptions = _parse_assumptions(assumptions_rows)
    probability_by_age = _parse_probability_table(probability_rows)

    return WorkbookReferenceData(
        assumptions=assumptions,
        probability_by_age=probability_by_age,
    )


@lru_cache(maxsize=1)
def load_workbook_projection_reference():
    workbook_path = Path(settings.BASE_DIR) / "sample cashflow model.xlsx"
    shared_strings, sheets = _read_workbook_sheets(workbook_path)
    return _parse_calculation_projection_rows_from_sheet(
        sheets[CALCULATION_SHEET],
        shared_strings,
    )


def _read_workbook_sheets(workbook_path):
    with zipfile.ZipFile(workbook_path) as workbook_zip:
        shared_strings = _load_shared_strings(workbook_zip)
        workbook_xml = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
        relationships_xml = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
        relationship_map = {
            relationship.attrib["Id"]: f"xl/{relationship.attrib['Target']}"
            for relationship in relationships_xml
        }

        sheets = {}
        for sheet in workbook_xml.find("a:sheets", XML_NAMESPACES):
            relationship_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            sheet_name = sheet.attrib["name"]
            sheets[sheet_name] = workbook_zip.read(relationship_map[relationship_id])

    return shared_strings, sheets


def _load_shared_strings(workbook_zip):
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []

    shared_strings = []
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    for string_item in root.findall("a:si", XML_NAMESPACES):
        shared_strings.append(
            "".join(
                text_node.text or ""
                for text_node in string_item.iterfind(".//a:t", XML_NAMESPACES)
            )
        )
    return shared_strings


def _extract_sheet_rows(sheet_xml, shared_strings):
    sheet_root = ET.fromstring(sheet_xml)
    extracted_rows = []

    for row in sheet_root.findall(".//a:sheetData/a:row", XML_NAMESPACES):
        values = []
        for cell in row.findall("a:c", XML_NAMESPACES):
            values.append(_read_cell_value(cell, shared_strings))
        if any(value != "" for value in values):
            extracted_rows.append(values)

    return extracted_rows


def _read_cell_value(cell, shared_strings):
    value_node = cell.find("a:v", XML_NAMESPACES)
    if value_node is None:
        return ""

    raw_value = value_node.text or ""
    if cell.attrib.get("t") == "s" and raw_value.isdigit():
        string_index = int(raw_value)
        if string_index < len(shared_strings):
            return shared_strings[string_index]

    return raw_value


def _parse_assumptions(rows):
    assumption_map = {
        row[0]: row[1]
        for row in rows[1:]
        if len(row) >= 2 and row[0]
    }

    return WorkbookAssumptions(
        valuation_date=_excel_serial_to_date(assumption_map["valuation_date"]),
        discount_rate=Decimal(assumption_map["discount_rate"]),
        salary_increase_rate=Decimal(assumption_map["salary_increase_rate"]),
        retirement_age=int(Decimal(assumption_map["retirement_age"])),
    )


def _parse_probability_table(rows):
    probability_by_age = {}
    for row in rows[1:]:
        if len(row) < 3:
            continue

        age = int(Decimal(row[0]))
        probability_by_age[age] = ProbabilityTableEntry(
            age=age,
            qx=Decimal(row[1]),
            px=Decimal(row[2]),
        )

    return probability_by_age


def _parse_calculation_projection_rows_from_sheet(sheet_xml, shared_strings):
    projection_rows = []
    sheet_root = ET.fromstring(sheet_xml)

    for row in sheet_root.findall(".//a:sheetData/a:row", XML_NAMESPACES):
        cell_values = {}
        for cell in row.findall("a:c", XML_NAMESPACES):
            cell_reference = cell.attrib.get("r", "")
            column_name = "".join(character for character in cell_reference if character.isalpha())
            cell_values[column_name] = _read_cell_value(cell, shared_strings)

        age = cell_values.get("E", "")
        future_salary = cell_values.get("F", "")
        survival_probability = cell_values.get("G", "")
        death_probability = cell_values.get("H", "")
        expected_death_outflow = cell_values.get("I", "")
        if not age or not future_salary or not survival_probability or not death_probability or not expected_death_outflow:
            continue

        try:
            parsed_age = int(Decimal(age))
            parsed_future_salary = Decimal(future_salary)
            parsed_survival_probability = Decimal(survival_probability)
            parsed_death_probability = Decimal(death_probability)
            parsed_expected_death_outflow = Decimal(expected_death_outflow)
        except Exception:
            continue

        projection_rows.append(
            WorkbookProjectionRow(
                age=parsed_age,
                future_salary=parsed_future_salary,
                survival_probability=parsed_survival_probability,
                death_probability=parsed_death_probability,
                expected_death_outflow=parsed_expected_death_outflow,
            )
        )

    return projection_rows


def _excel_serial_to_date(raw_value):
    excel_epoch = date(1899, 12, 30)
    serial_number = int(Decimal(raw_value))
    return excel_epoch + timedelta(days=serial_number)
