from dataclasses import dataclass
from decimal import Decimal

from .csv_parser import EmployeeInputRow, ParsedCsvResult
from .workbook_reference import WorkbookAssumptions, WorkbookReferenceData, load_workbook_reference_data


class CalculationError(Exception):
    """Raised when workbook-derived calculations cannot be completed."""


@dataclass(frozen=True)
class ProjectionRow:
    emp_id: int
    emp_name: str
    age: int
    future_salary: Decimal
    survival_probability: Decimal
    death_probability: Decimal
    expected_death_outflow: Decimal


@dataclass(frozen=True)
class CalculationResult:
    assumptions: WorkbookAssumptions
    projections: list[ProjectionRow]

    @property
    def output_row_count(self):
        return len(self.projections)


def run_calculations(parsed_csv: ParsedCsvResult, reference_data: WorkbookReferenceData | None = None):
    workbook_reference = reference_data or load_workbook_reference_data()
    projections = []

    for employee in parsed_csv.rows:
        projections.extend(
            _calculate_employee_projections(
                employee,
                workbook_reference,
            )
        )

    return CalculationResult(
        assumptions=workbook_reference.assumptions,
        projections=projections,
    )


def _calculate_employee_projections(
    employee: EmployeeInputRow,
    workbook_reference: WorkbookReferenceData,
):
    assumptions = workbook_reference.assumptions
    current_age = _calculate_current_age(employee, assumptions)

    if current_age >= assumptions.retirement_age:
        return []

    growth_factor = Decimal("1") + assumptions.salary_increase_rate
    future_salary = employee.salary * growth_factor
    projections = []

    for age in range(current_age, assumptions.retirement_age):
        probability_entry = workbook_reference.probability_by_age.get(age)
        if probability_entry is None:
            raise CalculationError(
                f"Lookup probability data is missing for age {age}."
            )

        expected_death_outflow = future_salary * probability_entry.px * probability_entry.qx
        projections.append(
            ProjectionRow(
                emp_id=employee.emp_id,
                emp_name=employee.emp_name,
                age=age,
                future_salary=future_salary,
                survival_probability=probability_entry.px,
                death_probability=probability_entry.qx,
                expected_death_outflow=expected_death_outflow,
            )
        )
        future_salary *= growth_factor

    return projections


def _calculate_current_age(employee: EmployeeInputRow, assumptions: WorkbookAssumptions):
    age_in_days = (assumptions.valuation_date - employee.date_birth).days + 1
    return int(Decimal(age_in_days) / Decimal("365.25"))
