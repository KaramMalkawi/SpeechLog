import pytest

from apps.tenancy.models import Community
from core.enums import PartnerScope
from core.tenancy import TenantContext
from tests.factories import CommunityFactory


@pytest.mark.django_db
def test_community_has_city_id_from_foreign_key():
    community = CommunityFactory()
    assert community.city_id == community.city.id


@pytest.mark.django_db
def test_community_type_defaults_to_general():
    community = CommunityFactory()
    assert community.community_type == Community.CommunityType.GENERAL


@pytest.mark.django_db
def test_community_supports_all_types(city):
    for community_type in Community.CommunityType:
        community = CommunityFactory(city=city, community_type=community_type)
        assert community.community_type == community_type


def test_partner_scope_enum_values():
    assert PartnerScope.COMMUNITY == "community"
    assert PartnerScope.CITY_WIDE == "city_wide"
    assert set(PartnerScope.values) == {"community", "city_wide"}
