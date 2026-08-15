from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import TenantScopedModel


class Post(TenantScopedModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    caption = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self) -> str:
        return f"Post {self.id} by {self.creator_id}"


class PostImage(TenantScopedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image_key = models.CharField(max_length=512)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["post", "order"], name="uniq_post_image_order")
        ]

    def __str__(self) -> str:
        return f"Image {self.order} of {self.post_id}"


class PostLike(TenantScopedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="uniq_post_like_per_user")
        ]

    def __str__(self) -> str:
        return f"{self.user_id} likes {self.post_id}"


class PostComment(TenantScopedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    # single-level nesting: parent may be None or point to a top-level comment
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        # enforce single-level nesting: parent cannot itself have a parent
        if self.parent_id:
            if self.parent.parent_id:
                raise ValidationError("Only single-level comment nesting is allowed")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Comment {self.id} on {self.post_id} by {self.user_id}"
