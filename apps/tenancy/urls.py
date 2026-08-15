from django.urls import path

from apps.tenancy.views import (
    CountryListView,
    OperationalCityListView,
    OperationalCountryListView,
)

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path(
        "countries/nationalities/",
        CountryListView.as_view(),
        {"purpose": "nationality"},
        name="country-nationalities",
    ),
    path(
        "countries/residence/",
        CountryListView.as_view(),
        {"purpose": "residence"},
        name="country-residence",
    ),
    path(
        "operational-countries/",
        OperationalCountryListView.as_view(),
        name="operational-country-list",
    ),
    path(
        "operational-cities/",
        OperationalCityListView.as_view(),
        name="operational-city-list",
    ),
]
