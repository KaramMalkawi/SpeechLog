from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.permissions import IsPlatformAdmin
from apps.tenancy.selectors import (
    get_nationality_countries,
    get_residence_countries,
    list_cities_for_country,
    list_operational_countries,
)


class CountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()


class OperationalCountrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    slug = serializers.CharField()
    is_active = serializers.BooleanField()


class OperationalCitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    is_active = serializers.BooleanField()
    country_id = serializers.UUIDField()
    country_name = serializers.CharField()
    country_code = serializers.CharField()


class CountryListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["tenancy"],
        summary="List countries",
        parameters=[
            OpenApiParameter(
                name="purpose",
                enum=["nationality", "residence"],
                required=False,
                description=(
                    "nationality = ISO countries via pycountry; "
                    "residence = allowed residence codes"
                ),
            ),
        ],
        responses={200: CountrySerializer(many=True)},
    )
    def get(self, request, purpose: str | None = None):
        purpose = purpose or request.query_params.get("purpose", "nationality")
        if purpose == "residence":
            countries = get_residence_countries()
        else:
            countries = get_nationality_countries()
        return Response(CountrySerializer(countries, many=True).data)


class OperationalCountryListView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["tenancy"],
        summary="List operational countries",
        description="DB countries used for city/tenancy structure. Admin only.",
        responses={200: OperationalCountrySerializer(many=True)},
    )
    def get(self, request):
        countries = list_operational_countries(active_only=True)
        payload = [
            {
                "id": country.id,
                "name": country.name,
                "code": country.code,
                "slug": country.slug,
                "is_active": country.is_active,
            }
            for country in countries
        ]
        return Response(OperationalCountrySerializer(payload, many=True).data)


class OperationalCityListView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["tenancy"],
        summary="List operational cities",
        description="Cities for a given operational country. Admin only.",
        parameters=[
            OpenApiParameter(
                name="country_id",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Operational country UUID",
            ),
        ],
        responses={200: OperationalCitySerializer(many=True)},
    )
    def get(self, request):
        country_id = request.query_params.get("country_id")
        if not country_id:
            return Response(
                {"detail": "country_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            country_uuid = UUID(str(country_id))
        except ValueError:
            return Response(
                {"detail": "Invalid country_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cities = list_cities_for_country(country_id=country_uuid, active_only=True)
        payload = [
            {
                "id": city.id,
                "name": city.name,
                "slug": city.slug,
                "is_active": city.is_active,
                "country_id": city.country_id,
                "country_name": city.country.name,
                "country_code": city.country.code,
            }
            for city in cities
        ]
        return Response(OperationalCitySerializer(payload, many=True).data)
