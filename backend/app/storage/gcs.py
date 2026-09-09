"""Google Cloud Storage integration for production media assets.

The application remains local-first when GCS_BUCKET is not configured, which
keeps local development simple. When a bucket is configured, processed scene
renders and final films are uploaded to Google Cloud Storage using Application
Default Credentials (ADC).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opentelemetry import trace

tracer = trace.get_tracer("thats-a-wrap-backend.google-cloud-storage")


class GCSStorageError(RuntimeError):
    """Raised when a Google Cloud Storage operation fails."""


class Storage:
    """Local-first storage with an optional Google Cloud Storage adapter."""

    def __init__(self, bucket_name: str | None = None, project_id: str | None = None):
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.bucket = None
        self.client = None

        if bucket_name:
            try:
                from google.cloud import storage

                # Uses Application Default Credentials. On Cloud Run this uses
                # the service account attached to the service; locally it uses
                # `gcloud auth application-default login`.
                self.client = storage.Client(project=project_id or None)
                self.bucket = self.client.bucket(bucket_name)
            except Exception as exc:  # pragma: no cover - depends on local ADC
                raise GCSStorageError(
                    "Google Cloud Storage is configured but could not be initialized. "
                    "Check GOOGLE_CLOUD_PROJECT, GCS_BUCKET, and Application Default Credentials."
                ) from exc

    @property
    def enabled(self) -> bool:
        return self.bucket is not None

    def upload(self, local_path: str, object_name: str, content_type: str | None = None) -> str:
        """Upload a local media file and return its gs:// URI."""
        path = Path(local_path)
        if not path.exists():
            raise GCSStorageError(f"Media file does not exist: {path}")
        if not self.bucket:
            return str(path)

        with tracer.start_as_current_span("google_cloud_storage_upload") as span:
            span.set_attribute("operation.type", "google_cloud_storage_upload")
            span.set_attribute("gcp.service", "storage.googleapis.com")
            span.set_attribute("gcp.bucket", self.bucket_name or "")
            span.set_attribute("gcp.object", object_name)
            span.set_attribute("media.size_bytes", path.stat().st_size)
            try:
                blob = self.bucket.blob(object_name)
                blob.upload_from_filename(str(path), content_type=content_type)
                uri = f"gs://{self.bucket_name}/{object_name}"
                span.set_attribute("gcp.storage_uri", uri)
                span.set_attribute("operation.status", "success")
                return uri
            except Exception as exc:
                span.record_exception(exc)
                span.set_attribute("operation.status", "failed")
                raise GCSStorageError(f"Google Cloud Storage upload failed: {exc}") from exc

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "Google Cloud Storage" if self.enabled else "local filesystem",
            "bucket_configured": bool(self.bucket_name),
            "bucket": self.bucket_name if self.bucket_name else None,
            "project": self.project_id if self.project_id else None,
        }
