from django.urls import path

from .views import dashboard, execution_detail, history

app_name = "executions"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("history/", history, name="history"),
    path("history/<int:execution_id>/", execution_detail, name="execution_detail"),
]
