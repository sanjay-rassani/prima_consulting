from django.db import models


def input_upload_path(instance, filename):
    return f"inputs/{filename}"


def output_upload_path(instance, filename):
    return f"outputs/{filename}"


class ExecutionRun(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    original_input_filename = models.CharField(max_length=255)
    original_output_filename = models.CharField(max_length=255, blank=True)
    input_file = models.FileField(upload_to=input_upload_path)
    output_file = models.FileField(upload_to=output_upload_path, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    rows_processed = models.PositiveIntegerField(default=0)
    output_rows = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_input_filename} ({self.get_status_display()})"
