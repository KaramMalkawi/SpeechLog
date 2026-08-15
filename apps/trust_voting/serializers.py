from __future__ import annotations

from rest_framework import serializers

from apps.trust_voting.models import TrustVote, TrustScore, VotingWindow


class TrustVoteSerializer(serializers.ModelSerializer):
    voter_full_name = serializers.CharField(source="voter.full_name", read_only=True)

    class Meta:
        model = TrustVote
        fields = ["id", "voting_window", "voter", "voter_full_name", "vote", "comment", "created_at"]
        read_only_fields = ["id", "voter_full_name", "created_at"]


class TrustScoreSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = TrustScore
        fields = ["user", "user_full_name", "score", "total_votes", "last_computed_at"]
        read_only_fields = fields


class VotingWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = VotingWindow
        fields = ["id", "event_id", "starts_at", "ends_at", "is_closed", "prompt_sent"]
        read_only_fields = fields
