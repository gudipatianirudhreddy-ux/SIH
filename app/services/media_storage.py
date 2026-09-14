import logging
import os
import uuid
from typing import Optional

from app.auth import supabase

logger = logging.getLogger(__name__)


class BaseStorageService:
    """Abstract interface for media file storage."""

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        bucket: str = "issue-media",
    ) -> str:
        """Uploads a file and returns its publicly accessible URL or storage reference."""
        raise NotImplementedError


class SupabaseStorageService(BaseStorageService):
    """Supabase Storage implementation.

    Integrates with Supabase Storage buckets (e.g. 'issue-media', 'solution-docs').
    Ensure a public bucket exists in your Supabase dashboard or storage permissions are configured.
    """

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        bucket: str = "issue-media",
    ) -> str:
        unique_name = f"{uuid.uuid4()}_{filename}"
        try:
            # Upload to Supabase storage bucket
            supabase.storage.from_(bucket).upload(
                path=unique_name,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            # Retrieve public URL
            public_url = supabase.storage.from_(bucket).get_public_url(unique_name)
            return public_url
        except Exception as exc:
            logger.warning(
                "Supabase Storage upload failed or bucket '%s' not configured (%s). Falling back to mock URL.",
                bucket,
                exc,
            )
            return f"https://mock-storage.sih.local/{bucket}/{unique_name}"


class LocalStorageService(BaseStorageService):
    """Local fallback / testing storage service."""

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        bucket: str = "issue-media",
    ) -> str:
        unique_name = f"{uuid.uuid4()}_{filename}"
        return f"https://mock-storage.sih.local/{bucket}/{unique_name}"


# Default storage service configured for application
_storage_service: Optional[BaseStorageService] = None


def get_storage_service() -> BaseStorageService:
    """Returns active storage service instance."""
    global _storage_service
    if _storage_service is None:
        # Use Supabase Storage if configured; fallback if not available
        supabase_url = os.getenv("SUPABASE_URL")
        if supabase_url and "supabase.co" in supabase_url:
            _storage_service = SupabaseStorageService()
        else:
            _storage_service = LocalStorageService()
    return _storage_service
