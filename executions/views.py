from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UploadCsvForm
from .models import ExecutionRun
from .services.calculations import CalculationError, run_calculations
from .services.csv_contract import EXPECTED_INPUT_HEADERS
from .services.output_csv import build_output_csv


def dashboard(request):
    if request.method == "POST":
        form = UploadCsvForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["input_file"]
            parsed_csv = form.cleaned_data["parsed_csv"]
            execution_run = ExecutionRun.objects.create(
                original_input_filename=uploaded_file.name,
                input_file=uploaded_file,
                status=ExecutionRun.Status.PROCESSING,
                rows_processed=parsed_csv.row_count,
            )
            try:
                calculation_result = run_calculations(parsed_csv)
            except CalculationError as exc:
                execution_run.status = ExecutionRun.Status.FAILED
                execution_run.error_message = str(exc)
                execution_run.save(update_fields=["status", "error_message", "updated_at"])
                form.add_error("input_file", str(exc))
            else:
                output_csv = build_output_csv(
                    calculation_result,
                    input_filename=uploaded_file.name,
                )
                execution_run.output_file.save(
                    output_csv.filename,
                    output_csv.content,
                    save=False,
                )
                execution_run.original_output_filename = output_csv.filename
                execution_run.status = ExecutionRun.Status.COMPLETED
                execution_run.output_rows = calculation_result.output_row_count
                execution_run.error_message = ""
                execution_run.save()
                messages.success(
                    request,
                    (
                        f"Input CSV validated and calculations completed successfully. "
                        f"{parsed_csv.row_count} input rows produced "
                        f"{calculation_result.output_row_count} calculation rows. "
                        f"Output CSV saved as {output_csv.filename}."
                    ),
                )
                return redirect("executions:dashboard")
    else:
        form = UploadCsvForm()

    execution_history = ExecutionRun.objects.all()
    context = {
        "form": form,
        "execution_history": execution_history[:5],
        "expected_headers": EXPECTED_INPUT_HEADERS,
        "latest_execution": execution_history.first(),
    }
    return render(request, "executions/dashboard.html", context)


def history(request):
    execution_history = ExecutionRun.objects.all()
    context = {
        "execution_history": execution_history,
    }
    return render(request, "executions/history.html", context)


def execution_detail(request, execution_id):
    execution = get_object_or_404(ExecutionRun, pk=execution_id)
    context = {
        "execution": execution,
    }
    return render(request, "executions/execution_detail.html", context)
