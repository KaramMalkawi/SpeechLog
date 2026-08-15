from django.urls import path

from apps.feed.views import FeedView

urlpatterns = [
    path("", FeedView.as_view(), name="feed-list"),
]
