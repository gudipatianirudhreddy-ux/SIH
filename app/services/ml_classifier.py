import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class IssueClassifier:
    """Interface / Placeholder for ML Issue Classification.

    NOTE FOR SIH EVALUATORS / CONTRIBUTORS:
    The actual deep learning model will be integrated here (e.g. PyTorch/ONNX/TensorFlow).
    Do NOT add CLIP or scikit-learn.
    When ready, simply replace the mock logic in `classify` or inject a production classifier.
    """

    DEFAULT_CATEGORIES = [
        "Roads & Potholes",
        "Garbage & Waste Management",
        "Water Supply & Drainage",
        "Electricity & Street Lighting",
        "Public Infrastructure",
    ]

    def classify(self, image_path_or_url: str) -> Dict[str, Optional[float]]:
        """Classifies an issue image into a societal problem category with confidence.

        Args:
            image_path_or_url: Local file path or remote storage URL of the issue image.

        Returns:
            dict containing:
                - 'category': predicted category string
                - 'confidence': confidence score between 0.0 and 1.0
        """
        logger.info(
            "[MOCK ML CLASSIFIER] Classifying media '%s'. (Development placeholder)",
            image_path_or_url,
        )

        # Keyword heuristics for prototype testing
        url_lower = image_path_or_url.lower()
        if any(k in url_lower for k in ["road", "pothole", "asphalt", "traffic"]):
            category = "Roads & Potholes"
            confidence = 0.94
        elif any(k in url_lower for k in ["garbage", "waste", "trash", "dump"]):
            category = "Garbage & Waste Management"
            confidence = 0.92
        elif any(k in url_lower for k in ["water", "leak", "drain", "flood"]):
            category = "Water Supply & Drainage"
            confidence = 0.91
        elif any(k in url_lower for k in ["light", "electric", "pole", "wire"]):
            category = "Electricity & Street Lighting"
            confidence = 0.89
        else:
            category = "Public Infrastructure"
            confidence = 0.85

        return {
            "category": category,
            "confidence": confidence,
        }


# Singleton instance for simple dependency injection
default_classifier = IssueClassifier()


def get_issue_classifier() -> IssueClassifier:
    """Returns active classifier instance."""
    return default_classifier
