"""Tests for S3 storage + AVIF conversion.

Includes unit tests (mocked S3) and one integration test that uploads
the website logo to the real Hetzner bucket.
"""

import io
import os
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from backend.s3_storage import (
    convert_to_avif,
    _ext_for_type,
    upload_image,
    upload_chat_image,
    download_image,
    get_presigned_url,
    delete_image,
)


# ---------------------------------------------------------------------------
# Helpers: create minimal test images in memory
# ---------------------------------------------------------------------------

def _make_png_bytes(width=10, height=10, color="red"):
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes(width=10, height=10):
    img = Image.new("RGB", (width, height), "blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_gif_bytes(width=10, height=10):
    img = Image.new("P", (width, height), 1)
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# AVIF conversion
# ---------------------------------------------------------------------------

def test_convert_to_avif_from_png():
    """PNG bytes are converted to AVIF."""
    png = _make_png_bytes()
    result, ct = convert_to_avif(png, "image/png")
    assert ct == "image/avif"
    assert len(result) > 0
    assert result != png


def test_convert_to_avif_from_jpeg():
    """JPEG bytes are converted to AVIF."""
    jpg = _make_jpeg_bytes()
    result, ct = convert_to_avif(jpg, "image/jpeg")
    assert ct == "image/avif"
    assert len(result) > 0


def test_convert_to_avif_from_webp():
    """WebP bytes are converted to AVIF."""
    img = Image.new("RGB", (10, 10), "green")
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    webp = buf.getvalue()
    result, ct = convert_to_avif(webp, "image/webp")
    assert ct == "image/avif"


def test_convert_passthrough_gif():
    """GIF passes through unconverted."""
    gif = _make_gif_bytes()
    result, ct = convert_to_avif(gif, "image/gif")
    assert ct == "image/gif"
    assert result == gif


def test_convert_passthrough_svg():
    """SVG passes through unconverted."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'
    result, ct = convert_to_avif(svg, "image/svg+xml")
    assert ct == "image/svg+xml"
    assert result == svg


def test_convert_rgba_png():
    """RGBA PNG (with transparency) converts to AVIF."""
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result, ct = convert_to_avif(buf.getvalue(), "image/png")
    assert ct == "image/avif"


# ---------------------------------------------------------------------------
# Extension mapping
# ---------------------------------------------------------------------------

def test_ext_for_type():
    assert _ext_for_type("image/avif") == "avif"
    assert _ext_for_type("image/gif") == "gif"
    assert _ext_for_type("image/svg+xml") == "svg"
    assert _ext_for_type("image/jpeg") == "avif"  # converted


# ---------------------------------------------------------------------------
# S3 upload (mocked)
# ---------------------------------------------------------------------------

@patch("backend.s3_storage._get_s3_client")
def test_upload_image_to_s3(mock_get_client):
    """upload_image converts and uploads to correct S3 key."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    png = _make_png_bytes()
    result = upload_image(
        instance_id=1,
        ticket_id=42,
        file_id="abc-123",
        image_bytes=png,
        original_filename="photo.png",
        content_type="image/png",
    )

    assert result["s3_key"] == "1/42/abc-123.avif"
    assert result["content_type"] == "image/avif"
    assert result["file_size_bytes"] > 0
    mock_client.put_object.assert_called_once()
    call_kwargs = mock_client.put_object.call_args[1]
    assert call_kwargs["Key"] == "1/42/abc-123.avif"
    assert call_kwargs["ContentType"] == "image/avif"


@patch("backend.s3_storage._get_s3_client")
def test_upload_chat_image_to_s3(mock_get_client):
    """upload_chat_image uses chat/ prefix in S3 key."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    png = _make_png_bytes()
    result = upload_chat_image(
        instance_id=5,
        file_id="def-456",
        image_bytes=png,
        original_filename="screenshot.png",
        content_type="image/png",
    )

    assert result["s3_key"] == "chat/5/def-456.avif"
    mock_client.put_object.assert_called_once()


@patch("backend.s3_storage._get_s3_client")
def test_upload_gif_preserves_format(mock_get_client):
    """GIF upload uses .gif extension, not .avif."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    gif = _make_gif_bytes()
    result = upload_image(
        instance_id=1, ticket_id=1, file_id="gif-id",
        image_bytes=gif, original_filename="anim.gif", content_type="image/gif",
    )

    assert result["s3_key"] == "1/1/gif-id.gif"
    assert result["content_type"] == "image/gif"


# ---------------------------------------------------------------------------
# S3 naming consistency
# ---------------------------------------------------------------------------

@patch("backend.s3_storage._get_s3_client")
def test_naming_consistency(mock_get_client):
    """S3 keys always follow {instance}/{ticket}/{file_id}.{ext} format."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    png = _make_png_bytes()
    r1 = upload_image(1, 10, "id-a", png, "my photo (1).png", "image/png")
    r2 = upload_image(2, 20, "id-b", png, "screénshot.png", "image/png")
    r3 = upload_image(3, 30, "id-c", _make_gif_bytes(), "funny.gif", "image/gif")

    # No original filenames leak into S3 keys
    assert r1["s3_key"] == "1/10/id-a.avif"
    assert r2["s3_key"] == "2/20/id-b.avif"
    assert r3["s3_key"] == "3/30/id-c.gif"


# ---------------------------------------------------------------------------
# S3 download / presign / delete (mocked)
# ---------------------------------------------------------------------------

@patch("backend.s3_storage._get_s3_client")
def test_download_image(mock_get_client):
    """download_image returns bytes and content type from S3."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"fake-avif-data"),
        "ContentType": "image/avif",
    }

    data, ct = download_image("1/42/abc.avif")
    assert data == b"fake-avif-data"
    assert ct == "image/avif"


@patch("backend.s3_storage._get_s3_client")
def test_get_presigned_url(mock_get_client):
    """get_presigned_url calls generate_presigned_url."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.generate_presigned_url.return_value = "https://example.com/signed"

    url = get_presigned_url("1/42/abc.avif")
    assert url == "https://example.com/signed"
    mock_client.generate_presigned_url.assert_called_once()


@patch("backend.s3_storage._get_s3_client")
def test_delete_image(mock_get_client):
    """delete_image calls delete_object on S3."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    delete_image("1/42/abc.avif")
    mock_client.delete_object.assert_called_once()


# ---------------------------------------------------------------------------
# Integration test: real S3 upload of website logo
# ---------------------------------------------------------------------------

def test_real_s3_upload_logo():
    """Upload profile_pic_1.jpg to real Hetzner S3, verify roundtrip, then delete."""
    from backend.config import S3_ACCESS_KEY, S3_ENDPOINT
    if not S3_ACCESS_KEY or not S3_ENDPOINT:
        pytest.skip("S3 not configured — skipping integration test")

    # Reset singleton so it uses real credentials
    import backend.s3_storage as mod
    mod._s3_client = None

    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "frontend", "static", "img", "profile_pic_1.jpg",
    )
    assert os.path.isfile(logo_path), f"Logo not found at {logo_path}"

    with open(logo_path, "rb") as f:
        original_bytes = f.read()

    # Upload (will convert JPEG → AVIF)
    result = upload_image(
        instance_id=0,
        ticket_id=0,
        file_id="integration-test-logo",
        image_bytes=original_bytes,
        original_filename="profile_pic_1.jpg",
        content_type="image/jpeg",
    )

    assert result["s3_key"] == "0/0/integration-test-logo.avif"
    assert result["content_type"] == "image/avif"
    assert result["file_size_bytes"] > 0
    # AVIF should be smaller than original JPEG
    print(f"Original JPEG: {len(original_bytes)} bytes → AVIF: {result['file_size_bytes']} bytes")

    # Download and verify
    downloaded, ct = download_image(result["s3_key"])
    assert ct == "image/avif"
    assert len(downloaded) == result["file_size_bytes"]

    # Verify it's a valid image
    img = Image.open(io.BytesIO(downloaded))
    assert img.format == "AVIF"

    # Presigned URL works
    url = get_presigned_url(result["s3_key"])
    assert "integration-test-logo.avif" in url

    # Clean up
    delete_image(result["s3_key"])
    print("Integration test passed: upload → download → verify → delete")
