from enum import Enum

class SubjectCategory(str, Enum):
    STEM = "stem"
    LANGUAGE = "language"
    HISTORY = "history"
    OTHER = "other"

STANDARD_SUBJECTS = {s.value for s in SubjectCategory if s != SubjectCategory.OTHER}
