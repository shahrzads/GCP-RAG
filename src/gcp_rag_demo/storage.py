"""Storage helpers for persisting artifacts to Google Cloud Storage."""

from pathlib import Path


class GCSArtifactStore:
    """Upload local files to a configured Google Cloud Storage bucket."""

    def __init__(self, project_id: str, bucket_name: str) -> None:
        try:
            from google.cloud import storage
        except ImportError as exc:  # pragma: no cover - depends on external package
            raise RuntimeError(
                "google-cloud-storage is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
            ) from exc

        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def upload_file(self, local_path: str, blob_name: str) -> str:
        """Upload one file and return its ``gs://`` URI."""
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(str(Path(local_path)))
        return self.build_uri(blob_name)

    def upload_text(self, blob_name: str, content: str, content_type: str) -> str:
        """Upload text content and return its ``gs://`` URI."""
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=content_type)
        return self.build_uri(blob_name)

    def upload_bytes(self, blob_name: str, content: bytes, content_type: str) -> str:
        """Upload raw bytes and return the resulting ``gs://`` URI."""
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=content_type)
        return self.build_uri(blob_name)

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob when present and report whether anything was removed."""
        blob = self._bucket.blob(blob_name)
        if not blob.exists(self._client):
            return False
        blob.delete()
        return True

    def download_text(self, blob_name: str) -> str:
        """Download text content from a blob."""
        blob = self._bucket.blob(blob_name)
        if not blob.exists(self._client):
            raise FileNotFoundError("Blob not found: {0}".format(self.build_uri(blob_name)))
        return blob.download_as_text()

    def build_uri(self, blob_name: str) -> str:
        """Return the ``gs://`` URI for a blob name in this bucket."""
        return "gs://{0}/{1}".format(self._bucket.name, blob_name)
