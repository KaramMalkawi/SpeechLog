from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/founders/", include("apps.founders.urls")),
    path("api/v1/tenancy/", include("apps.tenancy.urls")),
    path("api/v1/adminpanel/", include("apps.adminpanel.urls")),
    path("api/v1/events/", include("apps.events.urls")),
    path("api/v1/gatherings/", include("apps.gatherings.urls")),
    path("api/v1/feed/", include("apps.feed.urls")),
    path("api/v1/guidebook/", include("apps.guidebook.urls")),
]

if settings.API_DOCS_ENABLED:
    schema_view = SpectacularAPIView.as_view(authentication_classes=[], permission_classes=[])
    swagger_view = SpectacularSwaggerView.as_view(
        url_name="schema",
        authentication_classes=[],
        permission_classes=[],
    )
    urlpatterns += [
        path("api/v1/schema/", schema_view, name="schema"),
        path("api/v1/docs/", swagger_view, name="swagger-ui"),
    ]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
