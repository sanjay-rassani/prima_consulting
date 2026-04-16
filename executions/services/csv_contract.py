"""Workbook-derived CSV contract definitions."""

INPUT_ASSUMPTIONS_SHEET = "input_assumptions"
INPUT_DATA_SHEET = "input_data"
CALCULATION_SHEET = "calculation"
LOOKUP_PROBABILITY_SHEET = "lookup_probability"

EXPECTED_INPUT_HEADERS = [
    "emp_id",
    "emp_name",
    "date_birth",
    "date_joining",
    "salary",
]

INPUT_HEADER_DESCRIPTIONS = {
    "emp_id": "Unique employee identifier. Must be a positive integer.",
    "emp_name": "Employee full name. Cannot be blank.",
    "date_birth": "Date of birth from the workbook input. Accepts Excel serial dates or ISO dates.",
    "date_joining": "Date of joining from the workbook input. Accepts Excel serial dates or ISO dates.",
    "salary": "Current salary. Must be a non-negative decimal number.",
}
