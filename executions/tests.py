import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import UploadCsvForm
from .models import ExecutionRun
from .services.calculations import run_calculations
from .services.csv_parser import parse_uploaded_csv
from .services.output_csv import build_output_csv
from .services.workbook_reference import (
    load_workbook_projection_reference,
    load_workbook_reference_data,
)


class CsvParsingTests(TestCase):
    def test_parse_uploaded_csv_accepts_workbook_headers_and_normalizes_rows(self):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                "emp_id,emp_name,date_birth,date_joining,salary\n"
                "1,Employee 1,32546,45329,11280.25\n"
                "2,Employee 2,1995-12-29,2024-06-01,8029.80\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        parsed_csv = parse_uploaded_csv(uploaded_file)

        self.assertEqual(parsed_csv.headers, ["emp_id", "emp_name", "date_birth", "date_joining", "salary"])
        self.assertEqual(parsed_csv.row_count, 2)
        self.assertEqual(parsed_csv.rows[0].emp_id, 1)
        self.assertIsInstance(parsed_csv.rows[0].date_birth, date)
        self.assertEqual(parsed_csv.rows[1].salary, Decimal("8029.80"))

    def test_upload_form_rejects_invalid_headers(self):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                "emp_name,emp_id,date_birth,date_joining,salary\n"
                "Employee 1,1,32546,45329,11280.25\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        form = UploadCsvForm(files={"input_file": uploaded_file})

        self.assertFalse(form.is_valid())
        self.assertIn("CSV headers must exactly match", form.errors["input_file"][0])


class WorkbookCalculationTests(TestCase):
    def test_workbook_reference_data_loads_expected_assumptions(self):
        reference_data = load_workbook_reference_data()

        self.assertEqual(reference_data.assumptions.valuation_date, date(2024, 12, 31))
        self.assertEqual(reference_data.assumptions.discount_rate, Decimal("0.0545"))
        self.assertEqual(reference_data.assumptions.salary_increase_rate, Decimal("0.05"))
        self.assertEqual(reference_data.assumptions.retirement_age, 60)
        self.assertEqual(reference_data.probability_by_age[35].px, Decimal("0.99771049999999994"))
        self.assertEqual(reference_data.probability_by_age[35].qx, Decimal("0.0022895000000000003"))

    def test_run_calculations_matches_sample_workbook_projection(self):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                "emp_id,emp_name,date_birth,date_joining,salary\n"
                "1,Employee 1,32546,45329,11280.25\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        parsed_csv = parse_uploaded_csv(uploaded_file)
        calculation_result = run_calculations(parsed_csv)
        workbook_projection_reference = load_workbook_projection_reference()

        self.assertEqual(calculation_result.output_row_count, 25)
        self.assertEqual(len(workbook_projection_reference), 25)

        first_projection = calculation_result.projections[0]
        last_projection = calculation_result.projections[-1]

        self.assertEqual(first_projection.age, 35)
        self.assertEqual(first_projection.future_salary, Decimal("11844.2625"))
        self.assertAlmostEqual(float(first_projection.expected_death_outflow), 27.055353617173811, places=12)

        self.assertEqual(last_projection.age, 59)
        self.assertAlmostEqual(float(last_projection.future_salary), 38198.930322080334, places=8)
        self.assertAlmostEqual(float(last_projection.expected_death_outflow), 388.88203513265876, places=8)

        for calculated_row, workbook_row in zip(
            calculation_result.projections,
            workbook_projection_reference,
            strict=True,
        ):
            self.assertEqual(calculated_row.age, workbook_row.age)
            self.assertAlmostEqual(
                float(calculated_row.future_salary),
                float(workbook_row.future_salary),
                places=8,
            )
            self.assertAlmostEqual(
                float(calculated_row.survival_probability),
                float(workbook_row.survival_probability),
                places=12,
            )
            self.assertAlmostEqual(
                float(calculated_row.death_probability),
                float(workbook_row.death_probability),
                places=12,
            )
            self.assertAlmostEqual(
                float(calculated_row.expected_death_outflow),
                float(workbook_row.expected_death_outflow),
                places=8,
            )

    def test_build_output_csv_generates_expected_headers_and_rows(self):
        uploaded_file = SimpleUploadedFile(
            "employees.csv",
            (
                "emp_id,emp_name,date_birth,date_joining,salary\n"
                "1,Employee 1,32546,45329,11280.25\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        parsed_csv = parse_uploaded_csv(uploaded_file)
        calculation_result = run_calculations(parsed_csv)
        output_csv = build_output_csv(calculation_result, "employees.csv")
        csv_text = output_csv.content.read().decode("utf-8")
        workbook_projection_reference = load_workbook_projection_reference()
        generated_rows = list(csv.DictReader(StringIO(csv_text)))

        self.assertEqual(output_csv.filename, "employees_output.csv")
        self.assertIn(
            "emp_id,emp_name,age,future_salary,survival_probability,death_probability,expected_death_outflow",
            csv_text,
        )
        self.assertIn(
            "1,Employee 1,35,11844.2625,0.99771049999999994,0.0022895000000000003,27.05535361717381129309717868",
            csv_text,
        )
        self.assertEqual(len(generated_rows), len(workbook_projection_reference))

        for generated_row, workbook_row in zip(
            generated_rows,
            workbook_projection_reference,
            strict=True,
        ):
            self.assertEqual(int(generated_row["age"]), workbook_row.age)
            self.assertAlmostEqual(
                float(generated_row["future_salary"]),
                float(workbook_row.future_salary),
                places=8,
            )
            self.assertAlmostEqual(
                float(generated_row["survival_probability"]),
                float(workbook_row.survival_probability),
                places=12,
            )
            self.assertAlmostEqual(
                float(generated_row["death_probability"]),
                float(workbook_row.death_probability),
                places=12,
            )
            self.assertAlmostEqual(
                float(generated_row["expected_death_outflow"]),
                float(workbook_row.expected_death_outflow),
                places=8,
            )


class DashboardUploadTests(TestCase):
    def test_dashboard_saves_validated_csv_and_completed_history_record(self):
        with TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                uploaded_file = SimpleUploadedFile(
                    "employees.csv",
                    (
                        "emp_id,emp_name,date_birth,date_joining,salary\n"
                        "1,Employee 1,32546,45329,11280.25\n"
                        "2,Employee 2,36989,45445,8029.8\n"
                    ).encode("utf-8"),
                    content_type="text/csv",
                )

                response = self.client.post(
                    reverse("executions:dashboard"),
                    {"input_file": uploaded_file},
                    follow=True,
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    (
                        "Input CSV validated and calculations completed successfully. "
                        "2 input rows produced 62 calculation rows. "
                        "Output CSV saved as employees_output.csv."
                    ),
                )
                self.assertEqual(ExecutionRun.objects.count(), 1)

                execution = ExecutionRun.objects.get()
                self.assertEqual(execution.status, ExecutionRun.Status.COMPLETED)
                self.assertEqual(execution.rows_processed, 2)
                self.assertEqual(execution.output_rows, 62)
                self.assertEqual(execution.original_input_filename, "employees.csv")
                self.assertEqual(execution.original_output_filename, "employees_output.csv")
                self.assertTrue(execution.output_file.name.endswith("employees_output.csv"))

                output_text = execution.output_file.read().decode("utf-8")
                output_rows = list(csv.DictReader(StringIO(output_text)))
                self.assertIn(
                    "emp_id,emp_name,age,future_salary,survival_probability,death_probability,expected_death_outflow",
                    output_text,
                )
                self.assertIn("1,Employee 1,35,11844.2625", output_text)
                self.assertEqual(len(output_rows), 62)

    def test_history_and_detail_pages_show_downloadable_execution_artifacts(self):
        with TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                uploaded_file = SimpleUploadedFile(
                    "employees.csv",
                    (
                        "emp_id,emp_name,date_birth,date_joining,salary\n"
                        "1,Employee 1,32546,45329,11280.25\n"
                    ).encode("utf-8"),
                    content_type="text/csv",
                )

                self.client.post(
                    reverse("executions:dashboard"),
                    {"input_file": uploaded_file},
                    follow=True,
                )

                execution = ExecutionRun.objects.get()

                history_response = self.client.get(reverse("executions:history"))
                self.assertEqual(history_response.status_code, 200)
                self.assertContains(history_response, "Execution History")
                self.assertContains(history_response, "Download input")
                self.assertContains(history_response, "Download output")
                self.assertContains(history_response, execution.original_input_filename)

                detail_response = self.client.get(
                    reverse("executions:execution_detail", args=[execution.id])
                )
                self.assertEqual(detail_response.status_code, 200)
                self.assertContains(detail_response, "Execution Details")
                self.assertContains(detail_response, "Rows Processed")
                self.assertContains(detail_response, "Output Rows")
                self.assertContains(detail_response, execution.original_output_filename)

    def test_execution_output_contains_excel_matched_rows_for_sample_employee(self):
        with TemporaryDirectory() as temp_media_root:
            with self.settings(MEDIA_ROOT=temp_media_root):
                uploaded_file = SimpleUploadedFile(
                    "employees.csv",
                    (
                        "emp_id,emp_name,date_birth,date_joining,salary\n"
                        "1,Employee 1,32546,45329,11280.25\n"
                    ).encode("utf-8"),
                    content_type="text/csv",
                )

                self.client.post(
                    reverse("executions:dashboard"),
                    {"input_file": uploaded_file},
                    follow=True,
                )

                execution = ExecutionRun.objects.get()
                workbook_projection_reference = load_workbook_projection_reference()
                output_rows = list(
                    csv.DictReader(StringIO(execution.output_file.read().decode("utf-8")))
                )

                self.assertEqual(len(output_rows), len(workbook_projection_reference))

                for output_row, workbook_row in zip(
                    output_rows,
                    workbook_projection_reference,
                    strict=True,
                ):
                    self.assertEqual(int(output_row["emp_id"]), 1)
                    self.assertEqual(output_row["emp_name"], "Employee 1")
                    self.assertEqual(int(output_row["age"]), workbook_row.age)
                    self.assertAlmostEqual(
                        float(output_row["future_salary"]),
                        float(workbook_row.future_salary),
                        places=8,
                    )
                    self.assertAlmostEqual(
                        float(output_row["expected_death_outflow"]),
                        float(workbook_row.expected_death_outflow),
                        places=8,
                    )
