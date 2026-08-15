import pytest
from django.http import HttpResponse

from core.middleware import TenantMiddleware
from core.tenancy import get_tenant_context


@pytest.mark.django_db
def test_tenant_middleware_sets_context_from_header(community_a, rf):
    captured: dict = {}

    def get_response(request):
        captured["ctx"] = get_tenant_context()
        captured["community"] = getattr(request, "community", None)
        return HttpResponse("ok")

    middleware = TenantMiddleware(get_response)
    request = rf.get("/", HTTP_X_COMMUNITY_ID=str(community_a.id))
    middleware(request)

    assert captured["ctx"] is not None
    assert captured["ctx"].community_id == community_a.id
    assert captured["ctx"].city_id == community_a.city_id
    assert captured["community"] == community_a
