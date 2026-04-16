from django import forms

from .services.csv_parser import CsvValidationError, parse_uploaded_csv


class UploadCsvForm(forms.Form):
    input_file = forms.FileField(
        label="Input CSV file",
        help_text="Upload a CSV file that matches the Excel model input structure.",
    )

    def clean_input_file(self):
        uploaded_file = self.cleaned_data["input_file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a CSV file.")
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = cleaned_data.get("input_file")
        if not uploaded_file:
            return cleaned_data

        try:
            parsed_csv = parse_uploaded_csv(uploaded_file)
        except CsvValidationError as exc:
            self.add_error("input_file", exc.errors)
            return cleaned_data

        cleaned_data["parsed_csv"] = parsed_csv
        return cleaned_data
