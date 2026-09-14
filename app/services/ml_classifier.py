import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class IssueClassifier:
    """HTTP client for the dedicated SIH ML inference service."""

    def __init__(self, ml_service_url: Optional[str] = None, timeout: float = 30.0):
        self.ml_service_url = (
            ml_service_url or os.getenv("SIH_ML_SERVICE_URL", "http://localhost:8001")
        ).rstrip("/")
        self.timeout = timeout

    def classify(self, image_path_or_url: str) -> Dict[str, Any]:
        """Send an issue image to SIH-ML and return the best detection.

        The ML service exposes POST /predict and accepts the image as multipart
        form data. A media URL is downloaded by the backend before forwarding it.
        """
        try:
            image_bytes, filename, content_type = self._read_image(image_path_or_url)

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.ml_service_url}/predict",
                    files={
                        "file": (
                            filename,
                            image_bytes,
                            content_type,
                        )
                    },
                )
                response.raise_for_status()
                payload = response.json()

            detections = payload.get("detections") or []
            if not detections:
                logger.info("ML service returned no detections for '%s'", image_path_or_url)
                return {
                    "category": None,
                    "confidence": None,
                    "priority": payload.get("highest_priority"),
                    "bbox": None,
                }

            # Use the highest-confidence detection as the issue's primary category.
            best_detection = max(
                detections,
                key=lambda detection: float(detection.get("confidence") or 0.0),
            )

            return {
                "category": best_detection.get("category"),
                "confidence": best_detection.get("confidence"),
                "priority": best_detection.get("priority"),
                "bbox": best_detection.get("bbox"),
            }

        except (httpx.HTTPError, OSError, ValueError) as exc:
            logger.exception("ML classification failed for '%s': %s", image_path_or_url, exc)
            # Classification failure must not prevent the issue from being saved.
            return {
                "category": None,
                "confidence": None,
                "priority": None,
                "bbox": None,
            }

    @staticmethod
    def _read_image(image_path_or_url: str) -> tuple[bytes, str, str]:
        """Read an image from a local path or HTTP(S) URL."""
        if image_path_or_url.startswith(("http://", "https://")):
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(image_path_or_url)
                response.raise_for_status()
            filename = Path(image_path_or_url.split("?", 1)[0]).name or "issue.jpg"
            content_type = response.headers.get("content-type", "image/jpeg")
            return response.content, filename, content_type

        path = Path(image_path_or_url)
        return path.read_bytes(), path.name or "issue.jpg", "image/jpeg"


# Singleton instance for simple dependency injection
default_classifier = IssueClassifier()


def get_issue_classifier() -> IssueClassifier:
    """Return the active classifier instance."""
    return default_classifier
