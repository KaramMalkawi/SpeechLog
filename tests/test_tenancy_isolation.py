import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.tenancy.models import CityAnnouncement, CommunityAnnouncement
from core.tenancy import TenantContext, set_tenant_context
from tests.factories import CityAnnouncementFactory, CommunityAnnouncementFactory


@pytest.mark.django_db
def test_community_scoped_data_isolated_between_communities(community_a, community_b):
    announcement_a = CommunityAnnouncementFactory(
        community=community_a,
        title="Community A only",
    )
    announcement_b = CommunityAnnouncementFactory(
        community=community_b,
        title="Community B only",
    )

    set_tenant_context(TenantContext.from_community(community_a))
    visible = list(CommunityAnnouncement.objects.values_list("id", flat=True))

    assert visible == [announcement_a.id]
    assert announcement_b.id not in visible


@pytest.mark.django_db
def test_city_shared_data_visible_across_communities(community_a, community_b, city):
    shared = CityAnnouncementFactory(city=city, title="City-wide update")

    set_tenant_context(TenantContext.from_community(community_a))
    from_community_a = list(CityAnnouncement.objects.values_list("id", flat=True))

    set_tenant_context(TenantContext.from_community(community_b))
    from_community_b = list(CityAnnouncement.objects.values_list("id", flat=True))

    assert from_community_a == [shared.id]
    assert from_community_b == [shared.id]


@pytest.mark.django_db
def test_city_shared_data_not_visible_in_other_cities(community_a, community_other_city):
    CityAnnouncementFactory(city=community_a.city, title="Amman news")
    other_city_announcement = CityAnnouncementFactory(
        city=community_other_city.city,
        title="Other city news",
    )

    set_tenant_context(TenantContext.from_community(community_a))
    visible = list(CityAnnouncement.objects.values_list("id", flat=True))

    assert other_city_announcement.id not in visible


@pytest.mark.django_db
def test_health_check_endpoint_reports_service_status():
    client = APIClient()
    response = client.get(reverse("health-check"))

    assert response.status_code in {200, 503}
    assert "checks" in response.data
    assert "database" in response.data["checks"]
    assert "redis" in response.data["checks"]
