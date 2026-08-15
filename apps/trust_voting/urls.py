from django.urls import path

from apps.trust_voting.views import (
    SubmitVoteView,
    MyTrustScoreView,
    FounderTrustScoreView,
    CloseWindowAdminView,
)

urlpatterns = [
    path("windows/<uuid:window_id>/vote/", SubmitVoteView.as_view(), name="trust-submit-vote"),
    path("me/score/", MyTrustScoreView.as_view(), name="trust-my-score"),
    path("founders/<uuid:user_id>/score/", FounderTrustScoreView.as_view(), name="trust-founder-score"),
    path("windows/<uuid:window_id>/close/", CloseWindowAdminView.as_view(), name="trust-close-window"),
]
