"""S3-compatible object storage for ticket images with AVIF conversion.

All uploaded images (except SVG and GIF) are converted to AVIF format
for optimal compression before being stored in Hetzner Object Storage.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError
from PIL import Image

from backend.config import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT,
    S3_REGION,
    S3_SECRET_KEY,
)

logger = logging.getLogger(__name__)

_s3_client: Any = None

# Types that pass through without AVIF conversion
_PASSTHROUGH_TYPES = {"image/gif", "image/svg+xml"}


def _get_s3_client():
    """Lazy singleton S3 client."""
    global _s3_client
    if _s3_client is None:
        if not S3_ACCESS_KEY or not S3_SECRET_KEY or not S3_ENDPOINT:
            raise RuntimeError("S3 not configured — set S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT")
        _s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
        )
    return _s3_client


def convert_to_avif(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Convert raster image bytes to AVIF. SVG and GIF pass through unchanged.

    Returns (converted_bytes, final_content_type).
    """
    if content_type in _PASSTHROUGH_TYPES:
        return image_bytes, content_type

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "LA", "PA"):
        pass  # keep alpha
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="AVIF", quality=50)
    return buf.getvalue(), "image/avif"


def _ext_for_type(content_type: str) -> str:
    """Return file extension for a content type."""
    if content_type == "image/gif":
        return "gif"
    if content_type == "image/svg+xml":
        return "svg"
    return "avif"


def upload_image(
    instance_id: int,
    ticket_id: int,
    file_id: str,
    image_bytes: bytes,
    original_filename: str,
    content_type: str,
) -> dict:
    """Convert to AVIF and upload to S3 under ticket path.

    S3 key: {instance_id}/{ticket_id}/{file_id}.{ext}
    Returns {"s3_key", "content_type", "file_size_bytes"}.
    """
    converted, final_type = convert_to_avif(image_bytes, content_type)
    ext = _ext_for_type(final_type)
    s3_key = f"{instance_id}/{ticket_id}/{file_id}.{ext}"

    client = _get_s3_client()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=converted,
        ContentType=final_type,
    )

    return {
        "s3_key": s3_key,
        "content_type": final_type,
        "file_size_bytes": len(converted),
    }


def upload_chat_image(
    instance_id: int,
    file_id: str,
    image_bytes: bytes,
    original_filename: str,
    content_type: str,
) -> dict:
    """Convert to AVIF and upload to S3 under chat path (not yet on a ticket).

    S3 key: chat/{instance_id}/{file_id}.{ext}
    """
    converted, final_type = convert_to_avif(image_bytes, content_type)
    ext = _ext_for_type(final_type)
    s3_key = f"chat/{instance_id}/{file_id}.{ext}"

    client = _get_s3_client()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=converted,
        ContentType=final_type,
    )

    return {
        "s3_key": s3_key,
        "content_type": final_type,
        "file_size_bytes": len(converted),
    }


def download_image(s3_key: str) -> tuple[bytes, str]:
    """Download an image from S3. Returns (bytes, content_type)."""
    client = _get_s3_client()
    resp = client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    data = resp["Body"].read()
    ct = resp.get("ContentType", "image/avif")
    return data, ct


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a temporary presigned URL (default 1 hour)."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def delete_image(s3_key: str) -> None:
    """Delete an image from S3."""
    client = _get_s3_client()
    try:
        client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        logger.warning("Failed to delete S3 object %s: %s", s3_key, e)
