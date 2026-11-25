"""Domain models: everything that crosses a boundary is validated here."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# GitHub owner (39 chars max), then a repo name with at least one character other than a dot:
# "." and ".." would change the path of the API URLs built from it.
REPO_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,38}/[A-Za-z0-9._-]*[A-Za-z0-9_-][A-Za-z0-9._-]*$"
SHA_PATTERN = r"^[0-9a-fA-F]{7,64}$"


class PullRequestRef(BaseModel):
    """A pull request at one exact commit."""

    model_config = ConfigDict(frozen=True)

    repo: str = Field(pattern=REPO_PATTERN, max_length=140)
    number: int = Field(gt=0)
    head_sha: Annotated[str, StringConstraints(pattern=SHA_PATTERN, to_lower=True)]
    title: str = Field(max_length=500)

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.number}@{self.head_sha}"


class Severity(StrEnum):
    """Declared from least to most severe: `rank` relies on this order."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return list(Severity).index(self)


class Category(StrEnum):
    SECURITY = "security"
    BUG = "bug"
    QUALITY = "quality"


class Finding(BaseModel):
    """One problem reported by a reviewer, anchored to a line of a file."""

    path: str = Field(min_length=1, max_length=1024)
    line: int = Field(gt=0)
    severity: Severity
    category: Category
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    explanation: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class ReviewerOutput(BaseModel):
    """What a reviewer agent returns. An empty list means nothing to report."""

    findings: list[Finding] = Field(max_length=25)
