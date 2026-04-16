import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from django.core.files.base import ContentFile

from .calculations import CalculationResult

OUTPUT_HEADERS = [
    "emp_id",
    "emp_name",
    "age",
    "future_salary",
    "survival_probability",
    "death_probability",
    "expected_death_outflow",
]


@dataclass(frozen=True)
class OutputCsvArtifact:
    filename: str
    content: ContentFile


def build_output_csv(calculation_result: CalculationResult, input_filename: str):
    output_buffer = StringIO()
    writer = csv.writer(output_buffer)
    writer.writerow(OUTPUT_HEADERS)

    for projection in calculation_result.projections:
        writer.writerow(
            [
                projection.emp_id,
                projection.emp_name,
                projection.age,
                _decimal_to_string(projection.future_salary),
                _decimal_to_string(projection.survival_probability),
                _decimal_to_string(projection.death_probability),
                _decimal_to_string(projection.expected_death_outflow),
            ]
        )

    output_filename = f"{Path(input_filename).stem}_output.csv"
    output_content = ContentFile(output_buffer.getvalue().encode("utf-8"))

    return OutputCsvArtifact(
        filename=output_filename,
        content=output_content,
    )


def _decimal_to_string(value):
    return format(value, "f")
