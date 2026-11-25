"""Tests for the domain models."""

from typing import Any

import pytest
from pydantic import ValidationError

from pr_sentinel.models import Category, Finding, PullRequestRef, ReviewerOutput, Severity

SHA = "0123456789abcdef0123456789abcdef01234567"


def ref_data(**overrides: Any) -> dict[str, Any]:
    return {
        "repo": "octo-org/my.repo_1",
        "number": 12,
        "head_sha": SHA,
        "title": "Add login",
    } | overrides


def finding_data(**overrides: Any) -> dict[str, Any]:
    return {
        "path": "src/app.py",
        "line": 42,
        "severity": "high",
        "category": "security",
        "title": "SQL injection",
        "explanation": "User input is concatenated into the query.",
    } | overrides


def without(data: dict[str, Any], field: str) -> dict[str, Any]:
    return {name: value for name, value in data.items() if name != field}


def assert_rejected(model: type[Any], data: dict[str, Any], *loc: str | int) -> None:
    """The data is refused, and the only error is on the expected field."""
    with pytest.raises(ValidationError) as caught:
        model.model_validate(data)
    assert [error["loc"] for error in caught.value.errors()] == [loc]


# --- PullRequestRef ---------------------------------------------------------


def test_ref_accepts_valid_data() -> None:
    ref = PullRequestRef.model_validate(ref_data())
    assert ref.model_dump() == ref_data()


def test_ref_key_identifies_the_exact_commit() -> None:
    ref = PullRequestRef.model_validate(ref_data())
    assert ref.key == f"octo-org/my.repo_1#12@{SHA}"


@pytest.mark.parametrize("field", list(ref_data()))
def test_ref_is_frozen(field: str) -> None:
    ref = PullRequestRef.model_validate(ref_data())
    with pytest.raises(ValidationError, match="frozen"):
        setattr(ref, field, ref_data()[field])


def test_ref_is_hashable() -> None:
    first = PullRequestRef.model_validate(ref_data())
    second = PullRequestRef.model_validate(ref_data())
    assert len({first, second}) == 1


@pytest.mark.parametrize("field", list(ref_data()))
def test_ref_fields_are_required(field: str) -> None:
    assert_rejected(PullRequestRef, without(ref_data(), field), field)


@pytest.mark.parametrize(
    "repo", ["a/b", "octo/.github", "user_corp/repo", "o" * 39 + "/" + "r" * 100]
)
def test_ref_accepts_valid_repo(repo: str) -> None:
    assert PullRequestRef.model_validate(ref_data(repo=repo)).repo == repo


@pytest.mark.parametrize(
    "repo",
    [
        "",
        "octo",
        "/repo",
        "octo/",
        "octo/repo/extra",
        "-octo/repo",
        "octo/my repo",
        "octo/répo",
        "octo/repo?x=1",
        "octo/repo#1",
        "octo/.",
        "octo/..",
        "../repo",
        "octo/repo\n",
        "o" * 40 + "/repo",
        "o" * 39 + "/" + "r" * 101,
    ],
)
def test_ref_rejects_invalid_repo(repo: str) -> None:
    assert_rejected(PullRequestRef, ref_data(repo=repo), "repo")


@pytest.mark.parametrize("number", [0, -1])
def test_ref_rejects_non_positive_number(number: int) -> None:
    assert_rejected(PullRequestRef, ref_data(number=number), "number")


@pytest.mark.parametrize("length", [7, 40, 64])
def test_ref_accepts_sha_length(length: int) -> None:
    ref = PullRequestRef.model_validate(ref_data(head_sha="a" * length))
    assert ref.head_sha == "a" * length


@pytest.mark.parametrize("sha", ["", "a" * 6, "a" * 65, "g" * 40, "a" * 40 + "\n", " " + "a" * 40])
def test_ref_rejects_invalid_sha(sha: str) -> None:
    assert_rejected(PullRequestRef, ref_data(head_sha=sha), "head_sha")


def test_ref_normalises_sha_to_lowercase() -> None:
    upper = PullRequestRef.model_validate(ref_data(head_sha=SHA.upper()))
    assert upper.head_sha == SHA
    assert upper.key == PullRequestRef.model_validate(ref_data()).key


def test_ref_accepts_title_of_500_chars() -> None:
    assert PullRequestRef.model_validate(ref_data(title="t" * 500)).title == "t" * 500


def test_ref_rejects_title_over_500_chars() -> None:
    assert_rejected(PullRequestRef, ref_data(title="t" * 501), "title")


# --- Enums ------------------------------------------------------------------


def test_severity_values() -> None:
    assert [s.value for s in Severity] == ["low", "medium", "high", "critical"]


def test_severity_rank_orders_from_low_to_critical() -> None:
    shuffled = [Severity.HIGH, Severity.CRITICAL, Severity.LOW, Severity.MEDIUM]
    assert sorted(shuffled, key=lambda s: s.rank) == [
        Severity.LOW,
        Severity.MEDIUM,
        Severity.HIGH,
        Severity.CRITICAL,
    ]


def test_category_values() -> None:
    assert [c.value for c in Category] == ["security", "bug", "quality"]


# --- Finding ----------------------------------------------------------------


def test_finding_accepts_valid_data() -> None:
    finding = Finding.model_validate(finding_data())
    assert finding.model_dump() == finding_data()
    assert finding.severity is Severity.HIGH
    assert finding.category is Category.SECURITY


@pytest.mark.parametrize("field", list(finding_data()))
def test_finding_fields_are_required(field: str) -> None:
    assert_rejected(Finding, without(finding_data(), field), field)


@pytest.mark.parametrize("line", [0, -1])
def test_finding_rejects_non_positive_line(line: int) -> None:
    assert_rejected(Finding, finding_data(line=line), "line")


@pytest.mark.parametrize("field", ["severity", "category"])
def test_finding_rejects_unknown_enum_value(field: str) -> None:
    assert_rejected(Finding, finding_data(**{field: "unknown"}), field)


def test_finding_rejects_empty_path() -> None:
    assert_rejected(Finding, finding_data(path=""), "path")


@pytest.mark.parametrize("field", ["title", "explanation"])
def test_finding_rejects_blank_text(field: str) -> None:
    assert_rejected(Finding, finding_data(**{field: "  \n"}), field)


@pytest.mark.parametrize("field", ["title", "explanation"])
def test_finding_strips_text(field: str) -> None:
    finding = Finding.model_validate(finding_data(**{field: "  text \n"}))
    assert getattr(finding, field) == "text"


LIMITS = [("path", 1024), ("title", 200), ("explanation", 2000)]


@pytest.mark.parametrize(("field", "limit"), LIMITS)
def test_finding_accepts_text_at_limit(field: str, limit: int) -> None:
    finding = Finding.model_validate(finding_data(**{field: "x" * limit}))
    assert getattr(finding, field) == "x" * limit


@pytest.mark.parametrize(("field", "limit"), LIMITS)
def test_finding_rejects_text_over_limit(field: str, limit: int) -> None:
    assert_rejected(Finding, finding_data(**{field: "x" * (limit + 1)}), field)


# --- ReviewerOutput ---------------------------------------------------------


@pytest.mark.parametrize("count", [0, 1, 25])
def test_output_accepts_up_to_25_findings(count: int) -> None:
    output = ReviewerOutput.model_validate({"findings": [finding_data()] * count})
    assert len(output.findings) == count


def test_output_rejects_26_findings() -> None:
    assert_rejected(ReviewerOutput, {"findings": [finding_data()] * 26}, "findings")


def test_output_requires_findings() -> None:
    assert_rejected(ReviewerOutput, {}, "findings")


def test_output_rejects_an_invalid_finding() -> None:
    data = {"findings": [finding_data(), finding_data(line=0)]}
    assert_rejected(ReviewerOutput, data, "findings", 1, "line")
