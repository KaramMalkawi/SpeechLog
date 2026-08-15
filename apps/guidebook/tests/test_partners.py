from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import CommunityMembership, User
from apps.accounts.services import mark_user_verified
from apps.guidebook.models import PartnerCategory, PartnerScope
from apps.guidebook.services import create_partner
from apps.tenancy.models import City, Community, Country


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def country(db):
    country, _ = Country.objects.get_or_create(
        code="JO",
        defaults={"name": "Jordan", "slug": "jordan"},
    )
    return country


@pytest.fixture
def city(db, country):
    city, _ = City.objects.get_or_create(
        country=country,
        slug="amman-guidebook",
        defaults={"name": "Amman"},
    )
    return city


@pytest.fixture
def community(db, city):
    return Community.objects.create(
        city=city,
        name="Amman Expats",
        slug="amman-expats",
        community_type=Community.CommunityType.GENERAL,
    )


def _user(*, email: str, role: str, community: Community) -> User:
    user = User.objects.create_user(
        email=email,
        password="DemoPass123!",
        full_name=email.split("@")[0],
        role=role,
        active_community_id=community.id,
    )
    mark_user_verified(user)
    CommunityMembership.objects.create(
        user=user,
        community_id=community.id,
        city_id=community.city_id,
        role=CommunityMembership.Role.MEMBER,
    )
    return user


@pytest.fixture
def member_user(db, community):
    return _user(email="member@test.com", role=User.Role.MEMBER, community=community)


@pytest.fixture
def non_member_user(db, community):
    return _user(
        email="guest@test.com", role=User.Role.NON_MEMBER, community=community
    )


@pytest.fixture
def partner(db, city):
    return create_partner(
        city_id=city.id,
        name="The Noodle House",
        scope=PartnerScope.CITY_WIDE,
        category=PartnerCategory.RESTAURANT,
        area="DIFC",
        short_description="Authentic Pan-Asian cuisine.",
        description="Full description.",
        discount_percent=15,
        rating="4.7",
        address="Gate Village, Building 4",
        is_active=True,
    )


@pytest.mark.django_db
def test_list_partners_city_wide(api_client, member_user, partner, community):
    api_client.force_authenticate(user=member_user)
    response = api_client.get(
        "/api/v1/guidebook/partners/",
        {"community_id": str(community.id)},
    )
    assert response.status_code == 200
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["name"] == "The Noodle House"
    assert results[0]["discount_label"] == "15%OFF"
    assert results[0]["viewer_access"] == "member"
    assert results[0]["category_label"] == "Restaurant"


@pytest.mark.django_db
def test_non_member_access_locked(api_client, non_member_user, partner, community):
    api_client.force_authenticate(user=non_member_user)
    response = api_client.get(
        f"/api/v1/guidebook/partners/{partner.id}/",
        {"city_id": str(partner.city_id)},
    )
    assert response.status_code == 200
    assert response.data["viewer_access"] == "locked"


@pytest.mark.django_db
def test_community_partner_isolated(api_client, member_user, city, community):
    other = Community.objects.create(
        city=city,
        name="Other Expats",
        slug="other-expats",
        community_type=Community.CommunityType.GENERAL,
    )
    create_partner(
        city_id=city.id,
        name="Secret Spot",
        scope=PartnerScope.COMMUNITY,
        community_id=other.id,
        category=PartnerCategory.GROCERY,
    )
    api_client.force_authenticate(user=member_user)
    response = api_client.get(
        "/api/v1/guidebook/partners/",
        {"community_id": str(community.id)},
    )
    assert response.status_code == 200
    names = [row["name"] for row in response.data["results"]]
    assert "Secret Spot" not in names
