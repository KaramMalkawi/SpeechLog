from django.urls import path

from apps.adminpanel.views import AdminAuditLogListView

urlpatterns = [
    path("audit-logs/", AdminAuditLogListView.as_view(), name="admin-audit-log-list"),
]
