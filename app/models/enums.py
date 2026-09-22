from enum import Enum


class IssueStatus(str, Enum):
    REPORTED = "REPORTED"
    AI_CLASSIFIED = "AI_CLASSIFIED"
    VERIFIED = "VERIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    SOLUTION_SUBMITTED = "SOLUTION_SUBMITTED"
    EVALUATED = "EVALUATED"
    RESOLVED = "RESOLVED"


class SolutionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class IssuePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    SELECTED = "SELECTED"


class CollaborationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EvidenceType(str, Enum):
    PROGRESS = "PROGRESS"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


class SponsorshipStatus(str, Enum):
    PLEDGED = "PLEDGED"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    COMPLETED = "COMPLETED"

