from __future__ import annotations

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.guidebook.models import PartnerScope
from apps.guidebook.selectors import (
    get_partner_by_id,
    get_partner_for_city,
    list_partners,
    resolve_city_id_for_request,
)
from apps.guidebook.serializers import PartnerSerializer
from core.pagination import CreatedAtCursorPagination


class PartnerSortCursorPagination(CreatedAtCursorPagination):
    ordering = ("sort_order", "name", "id")


def _parse_optional_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ValidationError({"detail": "Invalid UUID."}) from exc


def _city_and_community_from_request(request) -> tuple[UUID | None, UUID | None]:
    city_id = _parse_optional_uuid(request.query_params.get("city_id"))
    community_id = _parse_optional_uuid(request.query_params.get("community_id"))

    community = getattr(request, "community", None)
    if community is not None:
        if community_id is None:
            community_id = community.id
        if city_id is None:
            city_id = community.city_id

    user = getattr(request, "user", None)
    if city_id is None:
        city_id = resolve_city_id_for_request(
            city_id=None,
            community_id=community_id,
            user=user if getattr(user, "is_authenticated", False) else None,
        )
    if community_id is None and user is not None and getattr(user, "is_authenticated", False):
        community_id = user.active_community_id
    return city_id, community_id


def _serialize_partners(request, partners) -> list:
    items = list(partners) if not isinstance(partners, list) else partners
    return PartnerSerializer(items, many=True, context={"request": request}).data


def _serialize_partner(request, partner) -> dict:
    return PartnerSerializer(partner, context={"request": request}).data


@extend_schema_view(
    get=extend_schema(
        tags=["guidebook"],
        summary="List guidebook partners for a city",
        parameters=[
            OpenApiParameter(name="city_id", required=False, type=str),
            OpenApiParameter(name="community_id", required=False, type=str),
            OpenApiParameter(name="category", required=False, type=str),
        ],
        responses={200: PartnerSerializer(many=True)},
    ),
)
class PartnerListView(generics.ListAPIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [AllowAny]
    pagination_class = PartnerSortCursorPagination
    serializer_class = PartnerSerializer

    def get_queryset(self):
        city_id, community_id = _city_and_community_from_request(self.request)
        if city_id is None:
            raise ValidationError(
                {
                    "city_id": (
                        "city_id, community_id, or an authenticated user with an "
                        "active community is required."
                    )
                }
            )
        return list_partners(
            city_id=city_id,
            community_id=community_id,
            category=self.request.query_params.get("category"),
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(_serialize_partners(request, page))
        return Response(_serialize_partners(request, queryset))


@extend_schema_view(
    get=extend_schema(
        tags=["guidebook"],
        summary="Partner detail",
        parameters=[
            OpenApiParameter(name="city_id", required=False, type=str),
            OpenApiParameter(name="community_id", required=False, type=str),
        ],
        responses={200: PartnerSerializer},
    ),
)
class PartnerDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, id: UUID):
        city_id, community_id = _city_and_community_from_request(request)
        if city_id is not None:
            partner = get_partner_for_city(partner_id=id, city_id=city_id)
        else:
            partner = get_partner_by_id(partner_id=id)
        if partner is None:
            raise NotFound("Partner not found.")
        # Community-scoped partners must match the viewer's community when known.
        if partner.scope == PartnerScope.COMMUNITY:
            if community_id is not None and partner.community_id != community_id:
                raise NotFound("Partner not found.")
        return Response(_serialize_partner(request, partner), status=status.HTTP_200_OK)
