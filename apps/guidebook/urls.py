from django.urls import path

from apps.guidebook.views import PartnerDetailView, PartnerListView

urlpatterns = [
    path("partners/", PartnerListView.as_view(), name="guidebook-partner-list"),
    path(
        "partners/<uuid:id>/",
        PartnerDetailView.as_view(),
        name="guidebook-partner-detail",
    ),
]
