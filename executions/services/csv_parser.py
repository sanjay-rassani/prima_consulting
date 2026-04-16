import csv
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO

from .csv_contract import EXPECTED_INPUT_HEADERS


class CsvValidationError(Exception):
    def __init__(self, errors):
        super().__init__("CSV validation failed.")
        self.errors = errors


@dataclass(frozen=True)
class EmployeeInputRow:
    emp_id: int
    emp_name: str
    date_birth: date
    date_joining: date
    salary: Decimal


@dataclass(frozen=True)
class ParsedCsvResult:
    headers: list[str]
    rows: list[EmployeeInputRow]

    @property
    def row_count(self):
        return len(self.rows)


def parse_uploaded_csv(uploaded_file):
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError(
            ["CSV file must be UTF-8 encoded."]
        ) from exc

    csv_reader = csv.reader(StringIO(text))
    rows = [row for row in csv_reader if any(cell.strip() for cell in row)]

    if not rows:
        raise CsvValidationError(["CSV file is empty."])

    headers = [header.strip() for header in rows[0]]
    errors = _validate_headers(headers)
    if errors:
        raise CsvValidationError(errors)

    normalized_rows = []
    for row_number, row in enumerate(rows[1:], start=2):
        normalized_row, row_errors = _parse_data_row(row_number, row, headers)
        errors.extend(row_errors)
        if normalized_row is not None:
            normalized_rows.append(normalized_row)

    if errors:
        raise CsvValidationError(errors)

    if not normalized_rows:
        raise CsvValidationError(["CSV file must contain at least one data row."])

    return ParsedCsvResult(headers=headers, rows=normalized_rows)


def _validate_headers(headers):
    errors = []

    if headers != EXPECTED_INPUT_HEADERS:
        errors.append(
            "CSV headers must exactly match the workbook input sheet order: "
            + ", ".join(EXPECTED_INPUT_HEADERS)
        )

    return errors


def _parse_data_row(row_number, row, headers):
    if len(row) != len(EXPECTED_INPUT_HEADERS):
        return None, [
            f"Row {row_number}: expected {len(EXPECTED_INPUT_HEADERS)} columns but found {len(row)}."
        ]

    values = {header: cell.strip() for header, cell in zip(headers, row)}
    errors = []

    emp_id = _parse_positive_int(values["emp_id"], row_number, "emp_id", errors)
    emp_name = _parse_required_text(values["emp_name"], row_number, "emp_name", errors)
    date_birth = _parse_date_value(values["date_birth"], row_number, "date_birth", errors)
    date_joining = _parse_date_value(
        values["date_joining"], row_number, "date_joining", errors
    )
    salary = _parse_decimal(values["salary"], row_number, "salary", errors)

    if errors:
        return None, errors

    return (
        EmployeeInputRow(
            emp_id=emp_id,
            emp_name=emp_name,
            date_birth=date_birth,
            date_joining=date_joining,
            salary=salary,
        ),
        [],
    )


def _parse_positive_int(value, row_number, field_name, errors):
    if not value:
        errors.append(f"Row {row_number}: {field_name} is required.")
        return None

    try:
        parsed_value = int(value)
    except ValueError:
        errors.append(f"Row {row_number}: {field_name} must be an integer.")
        return None

    if parsed_value <= 0:
        errors.append(f"Row {row_number}: {field_name} must be greater than zero.")
        return None

    return parsed_value


def _parse_required_text(value, row_number, field_name, errors):
    if not value:
        errors.append(f"Row {row_number}: {field_name} is required.")
        return None
    return value


def _parse_decimal(value, row_number, field_name, errors):
    if not value:
        errors.append(f"Row {row_number}: {field_name} is required.")
        return None

    try:
        parsed_value = Decimal(value)
    except InvalidOperation:
        errors.append(f"Row {row_number}: {field_name} must be a decimal number.")
        return None

    if parsed_value < 0:
        errors.append(f"Row {row_number}: {field_name} cannot be negative.")
        return None

    return parsed_value


def _parse_date_value(value, row_number, field_name, errors):
    if not value:
        errors.append(f"Row {row_number}: {field_name} is required.")
        return None

    try:
        serial_candidate = Decimal(value)
    except InvalidOperation:
        serial_candidate = None

    if serial_candidate is not None:
        if serial_candidate != serial_candidate.to_integral_value():
            errors.append(
                f"Row {row_number}: {field_name} Excel serial dates must be whole numbers."
            )
            return None

        serial_number = int(serial_candidate)
        if serial_number <= 0:
            errors.append(
                f"Row {row_number}: {field_name} Excel serial date must be greater than zero."
            )
            return None

        excel_epoch = date(1899, 12, 30)
        return excel_epoch + timedelta(days=serial_number)

    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(
            f"Row {row_number}: {field_name} must be an Excel serial date or ISO date."
        )
        return None
