from django.contrib import admin

from .models import ExecutionRun


@admin.register(ExecutionRun)
class ExecutionRunAdmin(admin.ModelAdmin):
    list_display = (
        "original_input_filename",
        "status",
        "rows_processed",
        "output_rows",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("original_input_filename", "original_output_filename")
