from __future__ import annotations

from enum import Enum


class ConsultationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Language(str, Enum):
    VN = "vn"
    EN = "en"
    FR = "fr"
    AR = "ar"
