from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class S3StorageError(Exception):
    """Raised when S3 operations fail."""


def is_s3_configured() -> bool:
    return bool(
        settings.AWS_S3_ACCESS_KEY_ID
        and settings.AWS_S3_SECRET_ACCESS_KEY
        and settings.AWS_STORAGE_BUCKET_NAME
    )


def _get_s3_client(*, for_presign: bool = False):
    if not is_s3_configured():
        raise S3StorageError("S3 is not configured.")

    endpoint_url = settings.AWS_S3_ENDPOINT_URL
    if for_presign and settings.AWS_S3_PUBLIC_ENDPOINT_URL:
        endpoint_url = settings.AWS_S3_PUBLIC_ENDPOINT_URL

    client_kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.AWS_S3_REGION_NAME,
        "aws_access_key_id": settings.AWS_S3_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_S3_SECRET_ACCESS_KEY,
        "config": Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"} if endpoint_url else {},
        ),
    }
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    return boto3.client(**client_kwargs)


def build_media_url(object_key: str) -> str:
    if not object_key:
        return ""
    base_url = settings.MEDIA_CDN_BASE_URL.rstrip("/")
    if base_url:
        return f"{base_url}/{object_key.lstrip('/')}"
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{object_key}"


def generate_presigned_upload_url(
    *,
    object_key: str,
    content_type: str,
    content_length: int,
    expires_in: int | None = None,
) -> dict[str, Any]:
    client = _get_s3_client(for_presign=True)
    expiry = expires_in or settings.PROFILE_PHOTO_PRESIGNED_EXPIRY

    try:
        upload_url = client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": object_key,
                "ContentType": content_type,
                "ContentLength": content_length,
            },
            ExpiresIn=expiry,
            HttpMethod="PUT",
        )
    except ClientError as exc:
        logger.exception("Failed to generate presigned upload URL for key=%s", object_key)
        raise S3StorageError("Could not create upload URL.") from exc

    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": expiry,
        "headers": {
            "Content-Type": content_type,
            "Content-Length": str(content_length),
        },
    }


def get_object_metadata(object_key: str) -> dict[str, Any] | None:
    client = _get_s3_client()
    try:
        response = client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=object_key,
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return None
        logger.exception("Failed to read object metadata for key=%s", object_key)
        raise S3StorageError("Could not verify uploaded file.") from exc

    return {
        "content_length": int(response.get("ContentLength", 0)),
        "content_type": response.get("ContentType", ""),
    }


def delete_object(object_key: str) -> None:
    if not object_key:
        return

    client = _get_s3_client()
    try:
        client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=object_key,
        )
    except ClientError as exc:
        logger.exception("Failed to delete object key=%s", object_key)
        raise S3StorageError("Could not delete file.") from exc


def put_object_bytes(
    *,
    object_key: str,
    body: bytes,
    content_type: str,
) -> None:
    """Upload bytes directly (seed/admin tooling). Prefer presigned uploads for clients."""
    if not object_key:
        raise S3StorageError("Object key is required.")
    client = _get_s3_client()
    try:
        client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=object_key,
            Body=body,
            ContentType=content_type,
            ContentLength=len(body),
        )
    except ClientError as exc:
        logger.exception("Failed to upload object key=%s", object_key)
        raise S3StorageError("Could not upload file.") from exc
