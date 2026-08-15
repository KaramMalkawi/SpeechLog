from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.trust_voting.models import VotingWindow, TrustVote, TrustScore
from apps.trust_voting.serializers import TrustVoteSerializer, TrustScoreSerializer, VotingWindowSerializer
from apps.trust_voting.services import close_voting_window_and_update_scores


class SubmitVoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, window_id):
        window = get_object_or_404(VotingWindow, pk=window_id, is_closed=False)
        # Only allow votes within window
        now = timezone.now()
        if not (window.starts_at <= now <= window.ends_at):
            return Response({"detail": "Voting window is not open."}, status=status.HTTP_400_BAD_REQUEST)

        # Only allow one vote per user - serializer will enforce unique constraint
        data = request.data.copy()
        data["voter"] = str(request.user.id)
        data["voting_window"] = str(window.id)
        serializer = TrustVoteSerializer(data=data)
        if serializer.is_valid():
            serializer.save(community_id=window.community_id, city_id=window.city_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTrustScoreView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TrustScoreSerializer

    def get_object(self):
        # return current user's score
        score, _ = TrustScore.objects.get_or_create(user=self.request.user)
        return score


class FounderTrustScoreView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = TrustScoreSerializer

    def get_object(self):
        user_id = self.kwargs["user_id"]
        return get_object_or_404(TrustScore, user_id=user_id)


class CloseWindowAdminView(APIView):
    # admin-only in real app; for now rely on platform admin bypass in permission stacks
    permission_classes = [IsAuthenticated]

    def post(self, request, window_id):
        result = close_voting_window_and_update_scores(window_id)
        if not result:
            return Response({"detail": "Window already closed or not found."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
