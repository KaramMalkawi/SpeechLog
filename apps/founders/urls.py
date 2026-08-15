from django.urls import path

from apps.founders.views import (
    CityFounderDetailView,
    CityFounderListCreateView,
    FounderApplicationDetailView,
    FounderApplicationListView,
    FounderApplicationSyncView,
    FounderChangePasswordView,
    FounderDashboardOverviewView,
)

urlpatterns = [
    path(
        "me/overview/",
        FounderDashboardOverviewView.as_view(),
        name="founder-dashboard-overview",
    ),
    path(
        "me/change-password/",
        FounderChangePasswordView.as_view(),
        name="founder-change-password",
    ),
    path(
        "applications/",
        FounderApplicationListView.as_view(),
        name="founder-application-list",
    ),
    path(
        "applications/sync/",
        FounderApplicationSyncView.as_view(),
        name="founder-application-sync",
    ),
    path(
        "applications/<uuid:application_id>/",
        FounderApplicationDetailView.as_view(),
        name="founder-application-detail",
    ),
    path("city-founders/", CityFounderListCreateView.as_view(), name="city-founder-list"),
    path(
        "city-founders/<uuid:founder_id>/",
        CityFounderDetailView.as_view(),
        name="city-founder-detail",
    ),
]
