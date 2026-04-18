from enum import Enum


class SeverityFlag(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UrgencyLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EMERGENCY = "Emergency"


class Language(str, Enum):
    EN = "en"
    VN = "vn"
    FR = "fr"
    AR = "ar"


class PipelineMode(str, Enum):
    UNIFIED = "unified"
    TWO_STEP = "two_step"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    CLEANING = "cleaning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
