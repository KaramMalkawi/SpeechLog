from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import List, Tuple

from django.core.cache import cache
from django.db.models import Count
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.models import Event
from apps.feed.models import Post, PostLike
from apps.feed.serializers import PostSerializer, EventSerializer, GatheringSerializer
from apps.gatherings.models import Gathering


# Simple cursor format: base64 encoded JSON {"ts": "ISO8601", "id": "uuid"}
# Items sorted by created_at desc, id desc for tie-breaker.


def decode_cursor(cursor: str):
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        obj = json.loads(decoded)
        ts = parse_datetime(obj.get("ts"))
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=utc)
        return ts, obj.get("id")
    except Exception:
        return None, None


def encode_cursor(ts: datetime, id: str) -> str:
    payload = {"ts": ts.isoformat(), "id": str(id)}
    raw = json.dumps(payload).encode()
    return base64.urlsafe_b64encode(raw).decode()


def _collect_feed_items(community_id, limit: int = 20, cursor: str | None = None):
    # fetch posts, events, gatherings within the community ordered by created_at desc
    # apply cursor filter if provided
    ts, cid = (None, None)
    if cursor:
        ts, cid = decode_cursor(cursor)

    def _filter_qs(qs):
        if ts:
            # created_at < ts OR (created_at == ts AND id < cid)
            return qs.filter(models.Q(created_at__lt=ts) | (models.Q(created_at=ts) & models.Q(id__lt=cid)))
        return qs

    # Using model managers directly
    posts_qs = Post.objects.filter(community_id=community_id)
    events_qs = Event.objects.filter(community_id=community_id)
    gatherings_qs = Gathering.objects.filter(community_id=community_id)

    if ts:
        posts_qs = posts_qs.filter(models.Q(created_at__lt=ts) | (models.Q(created_at=ts) & models.Q(id__lt=cid)))
        events_qs = events_qs.filter(models.Q(created_at__lt=ts) | (models.Q(created_at=ts) & models.Q(id__lt=cid)))
        gatherings_qs = gatherings_qs.filter(models.Q(created_at__lt=ts) | (models.Q(created_at=ts) & models.Q(id__lt=cid)))

    # Limit each source moderately to reduce over-fetching
    posts = list(posts_qs.order_by("-created_at")[: limit * 2])
    events = list(events_qs.order_by("-created_at")[: limit * 2])
    gatherings = list(gatherings_qs.order_by("-created_at")[: limit * 2])

    # Merge by created_at desc
    combined: List[Tuple[str, object]] = []
    for p in posts:
        combined.append(("post", p))
    for e in events:
        combined.append(("event", e))
    for g in gatherings:
        combined.append(("gathering", g))

    combined.sort(key=lambda t: (t[1].created_at, str(t[1].id)), reverse=True)
    sliced = combined[:limit]

    next_cursor = None
    if len(combined) > limit:
        last = sliced[-1][1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return sliced, next_cursor


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        community_id = request.user.active_community_id if hasattr(request.user, "active_community_id") else None
        if not community_id:
            return Response({"results": [], "next": None})

        cursor = request.query_params.get("cursor")
        cache_key = f"feed:{user.id}:{community_id}:{cursor or 'start'}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        items, next_cursor = _collect_feed_items(community_id, limit=20, cursor=cursor)

        results = []
        # eager annotate liked/counts for posts
        post_ids = [i[1].id for i in items if i[0] == "post"]
        post_likes = (
            PostLike.objects.filter(post_id__in=post_ids)
            .values("post_id")
            .annotate(c=Count("id"))
            .in_bulk(field_name="post_id")
        )

        for typ, obj in items:
            if typ == "post":
                # annotate counts
                likes_count = 0
                if obj.id in post_likes:
                    likes_count = post_likes[obj.id]["c"] if isinstance(post_likes[obj.id], dict) else post_likes[obj.id]
                comments_count = getattr(obj.comments, "count", lambda: 0)()
                user_liked = PostLike.objects.filter(post=obj, user=user).exists()
                ser = PostSerializer(obj, context={"request": request})
                data = ser.data
                data["likes_count"] = likes_count
                data["comments_count"] = obj.comments.count()
                data["user_liked"] = user_liked
                data["type"] = "post"
                results.append(data)
            elif typ == "event":
                ser = EventSerializer(obj, context={"request": request})
                data = ser.data
                data["type"] = "event"
                results.append(data)
            elif typ == "gathering":
                ser = GatheringSerializer(obj, context={"request": request})
                data = ser.data
                data["type"] = "gathering"
                results.append(data)

        resp = {"results": results, "next": next_cursor}
        # cache pages for short time (e.g., 30 seconds) to meet NFR low latency
        cache.set(cache_key, resp, timeout=30)
        return Response(resp)
