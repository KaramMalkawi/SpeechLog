import pytest

from core.tenancy import TenantContext, clear_tenant_context, set_tenant_context
from tests.factories import (
    CityAnnouncementFactory,
    CityFactory,
    CommunityAnnouncementFactory,
    CommunityFactory,
)


@pytest.fixture(autouse=True)
def _clear_tenant_context():
    clear_tenant_context()
    yield
    clear_tenant_context()


@pytest.fixture
def city(db):
    return CityFactory()


@pytest.fixture
def community_a(city):
    return CommunityFactory(city=city, slug="community-a")


@pytest.fixture
def community_b(city):
    return CommunityFactory(city=city, slug="community-b")


@pytest.fixture
def other_city(db):
    return CityFactory(slug="other-city")


@pytest.fixture
def community_other_city(other_city):
    return CommunityFactory(city=other_city, slug="community-other")


@pytest.fixture
def tenant_context(community_a):
    ctx = TenantContext.from_community(community_a)
    set_tenant_context(ctx)
    return ctx
