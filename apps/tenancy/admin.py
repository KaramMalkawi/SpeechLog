from django.contrib import admin

from apps.tenancy.models import City, CityAnnouncement, Community, CommunityAnnouncement, Country

admin.site.register(Country)
admin.site.register(City)
admin.site.register(Community)
admin.site.register(CityAnnouncement)
admin.site.register(CommunityAnnouncement)
