# Django CSV Calculator POC

This project is a Django-based proof of concept that replaces an Excel calculation model with Python code. It accepts employee input data as CSV, validates the file against the workbook-defined input structure, runs the calculation logic without Excel automation, generates an output CSV, and stores execution history with downloadable input and output files.

## What The POC Does

- Upload a CSV file that matches the workbook input structure
- Validate headers, encoding, and row-level values
- Reproduce the sample workbook calculation logic in Python
- Generate a downloadable output CSV
- Persist uploaded inputs, generated outputs, and execution history
- Show execution summary information in the UI

## Technology Stack

- Python 3.12
- Django 6
- SQLite for local persistence
- Django media storage for uploaded and generated files

## Project Structure

- `config/`: Django project settings and URL configuration
- `executions/models.py`: persisted execution history model
- `executions/views.py`: dashboard, history, and execution detail pages
- `executions/forms.py`: upload form and CSV validation entry point
- `executions/services/csv_contract.py`: workbook-derived input contract
- `executions/services/csv_parser.py`: CSV parsing and normalization
- `executions/services/workbook_reference.py`: workbook assumptions, lookup tables, and projection reference data
- `executions/services/calculations.py`: Python translation of the workbook calculations
- `executions/services/output_csv.py`: output CSV generation
- `templates/`: server-rendered UI templates
- `sample cashflow model.xlsx`: reference workbook used by the POC
- `examples/employees_sample.csv`: ready-to-use demo input file

## Setup

1. Create the virtual environment if it does not already exist:

```bash
python3 -m venv .venv
```

2. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Apply database migrations:

```bash
.venv/bin/python manage.py migrate
```

4. Start the development server:

```bash
.venv/bin/python manage.py runserver
```

5. Open the app in a browser:

`http://127.0.0.1:8000/`

## Demo Walkthrough

Use the checked-in sample CSV file:

- `examples/employees_sample.csv`

Demo steps:

1. Start the Django server.
2. Open the dashboard.
3. Upload `examples/employees_sample.csv`.
4. Click `Process`.
5. Confirm the latest execution summary shows:
   - execution status
   - number of input rows processed
   - number of output rows generated
6. Download the generated output CSV.
7. Open the `History` page and verify the run appears with input and output download links.
8. Open the execution details page to show the persisted record and file references.

## Input CSV Contract

The CSV must contain the headers below in this exact order:

```text
emp_id,emp_name,date_birth,date_joining,salary
```

Field expectations:

- `emp_id`: positive integer
- `emp_name`: required text
- `date_birth`: Excel serial date or ISO date
- `date_joining`: Excel serial date or ISO date
- `salary`: non-negative decimal

Validation currently checks:

- `.csv` file extension
- UTF-8 encoded content
- exact header order
- required values
- numeric validation for ids and salary
- date validation for Excel serial or ISO dates
- correct number of columns per row

## Output CSV Structure

The generated output file contains the following columns:

```text
emp_id,emp_name,age,future_salary,survival_probability,death_probability,expected_death_outflow
```

Each output row represents one projected year for one employee from current age up to, but not including, retirement age.

## Calculation Mapping From Excel

The current POC reproduces the sample workbook logic with these workbook-backed rules:

- Assumptions are loaded from the `input_assumptions` sheet.
- Mortality lookup values are loaded from the `lookup_probability` sheet.
- Current age is calculated as:

```text
INT((valuation_date - date_birth + 1) / 365.25)
```

- Future salary is projected yearly using:

```text
salary * (1 + salary_increase_rate)
```

- For each projected age, the app looks up:
  - `px` as survival probability
  - `qx` as death probability

- Expected death outflow is calculated as:

```text
future_salary * survival_probability * death_probability
```

## UI Pages

- `Dashboard`: upload CSV, run processing, view the latest execution summary, inspect recent executions
- `History`: browse all execution runs and download files
- `Execution Detail`: review one execution record and access its files

## Running Tests

Run the automated test suite:

```bash
.venv/bin/python manage.py test
```

Run Django system checks:

```bash
.venv/bin/python manage.py check
```

The tests cover:

- CSV parsing and validation
- workbook assumption loading
- calculation accuracy against the sample Excel workbook
- output CSV generation
- persisted execution history and files
- dashboard, history, and detail page behavior

## Current Limitations

- The POC is validated against the provided sample workbook scenario, not a broad family of workbook variants.
- The calculation engine currently reflects the workbook logic present in the supplied sample file.
- Discount rate is loaded from the workbook but is not yet used because the sample calculation output being replicated does not discount the yearly outflows.
- File storage is configured for local development rather than production infrastructure.
- Authentication and user-specific execution ownership are not included in this proof of concept.

## Extension Points

Areas that can be extended in a production version:

- support additional workbook tabs and calculation paths
- add background processing for larger files
- add user authentication and access control
- persist richer audit metadata
- export richer summaries or aggregated reports
- move file storage and database configuration to production services
