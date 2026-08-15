from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.didit.signatures import verify_didit_webhook
from apps.accounts.tasks import process_didit_webhook_task

logger = logging.getLogger(__name__)


class DiditWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        secret = settings.DIDIT_WEBHOOK_SECRET
        if not secret:
            return Response({"detail": "Webhook not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        raw_body = request.body
        headers = {key: value for key, value in request.headers.items()}
        payload, verified, verification_method = verify_didit_webhook(
            raw_body=raw_body,
            headers=headers,
            secret=secret,
        )

        if not verified:
            logger.warning(
                "Didit webhook signature verification failed body=%s",
                raw_body[:2000].decode("utf-8", errors="replace"),
            )
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_401_UNAUTHORIZED)

        event_id = payload.get("event_id")
        if not event_id:
            return Response({"detail": "Missing event_id."}, status=status.HTTP_400_BAD_REQUEST)

        process_didit_webhook_task.delay(str(event_id), payload, verification_method)
        return HttpResponse(status=204)
