"""Verify Google Cloud Storage configuration without printing credentials."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import settings
from backend.app.storage.gcs import Storage


def main() -> int:
    print("GOOGLE_CLOUD_PROJECT configured:", bool(settings.google_cloud_project))
    print("GCS_BUCKET configured:", bool(settings.gcs_bucket))
    if not settings.gcs_bucket:
        print("GCS CHECK: NOT CONFIGURED")
        print("Set GCS_BUCKET in backend/.env, then run this script again.")
        return 2

    try:
        gcs = Storage(settings.gcs_bucket, settings.google_cloud_project)
        print("GCS CLIENT INITIALIZED: True")
        print("PROVIDER:", gcs.status()["provider"])
        print("BUCKET:", settings.gcs_bucket)
        print("GCS CHECK: READY")
        return 0
    except Exception as exc:
        print("GCS CHECK: FAILED")
        print(type(exc).__name__ + ":", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
