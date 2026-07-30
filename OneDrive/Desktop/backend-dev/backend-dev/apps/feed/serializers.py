from __future__ import annotations

from django.core.cache import cache
from rest_framework import serializers

from apps.feed.models import Post, PostImage
from apps.gatherings.models import Gathering, GatheringAttendee
from apps.events.models import Event


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["image_key", "order"]


class PostSerializer(serializers.ModelSerializer):
    images = PostImageSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    user_liked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Post
        fields = ["id", "caption", "images", "created_at", "likes_count", "comments_count", "user_liked"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "starts_at", "cover_image_key", "created_at"]


class GatheringSerializer(serializers.ModelSerializer):
    exact_location = serializers.SerializerMethodField()

    class Meta:
        model = Gathering
        fields = ["id", "title", "area", "exact_location", "cover_image_key", "starts_at", "created_at"]

    def get_exact_location(self, obj: Gathering):
        # hide exact_location unless user is an attendee
        user = self.context.get("request").user
        if not user or not user.is_authenticated:
            return ""
        joined = GatheringAttendee.objects.filter(gathering=obj, user=user, is_active=True).exists()
        return obj.exact_location if joined else ""
