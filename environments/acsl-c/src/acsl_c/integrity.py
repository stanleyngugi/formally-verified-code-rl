"""Integrity checks for fixed-annotation (``mode=hints``) tasks.

Frama-C proves the program against the annotations it is given.  A model that is
allowed to delete or weaken those annotations can therefore manufacture reward.
Hints-mode tasks close that hole by requiring every token outside the generated
function body, including every ACSL annotation, to remain unchanged.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_FUNCTION_RE = re.compile(
    r"(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
    re.MULTILINE,
)
_CONTROL_WORDS = {"if", "for", "while", "switch"}
_TODO_RE = re.compile(r"//\s*TODO:\s*complete\s*", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class IntegrityResult:
    ok: bool
    annotations_unchanged: bool
    context_unchanged: bool
    reason: str = ""

    @property
    def score(self) -> float:
        return float(self.ok)


def _matching_brace(source: str, opening: int) -> int | None:
    """Find a C closing brace while ignoring strings and comments."""
    depth = 0
    i = opening
    state = "code"
    quote = ""
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "line-comment":
            if char == "\n":
                state = "code"
        elif state == "block-comment":
            if char == "*" and nxt == "/":
                state = "code"
                i += 1
        elif state == "string":
            if char == "\\":
                i += 1
            elif char == quote:
                state = "code"
        elif char == "/" and nxt == "/":
            state = "line-comment"
            i += 1
        elif char == "/" and nxt == "*":
            state = "block-comment"
            i += 1
        elif char in ('"', "'"):
            state = "string"
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _code_mask(source: str) -> str:
    """Mask comments and literals while preserving offsets and newlines."""
    chars = list(source)
    i = 0
    state = "code"
    quote = ""
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "line-comment":
            if char == "\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block-comment":
            chars[i] = "\n" if char == "\n" else " "
            if char == "*" and nxt == "/":
                chars[i + 1] = " "
                state = "code"
                i += 1
        elif state == "string":
            chars[i] = " "
            if char == "\\" and i + 1 < len(source):
                chars[i + 1] = " "
                i += 1
            elif char == quote:
                state = "code"
        elif char == "/" and nxt == "/":
            chars[i] = chars[i + 1] = " "
            state = "line-comment"
            i += 1
        elif char == "/" and nxt == "*":
            chars[i] = chars[i + 1] = " "
            state = "block-comment"
            i += 1
        elif char in ('"', "'"):
            chars[i] = " "
            state = "string"
            quote = char
        i += 1
    return "".join(chars)


def function_body_spans(source: str) -> list[tuple[int, int]]:
    """Locate top-level-looking C function bodies outside comments/literals."""
    masked = _code_mask(source)
    spans: list[tuple[int, int]] = []
    for match in _FUNCTION_RE.finditer(masked):
        if match.group("name") in _CONTROL_WORDS:
            continue
        opening = masked.rfind("{", match.start(), match.end())
        if any(start <= opening <= end for start, end in spans):
            continue
        closing = _matching_brace(source, opening)
        if closing is not None:
            spans.append((opening, closing))
    return spans


def first_function_body(source: str) -> tuple[int, int] | None:
    spans = function_body_spans(source)
    return spans[0] if spans else None


def _normalized_context(source: str, *, skeleton: bool) -> str | None:
    span = first_function_body(source)
    if span is None:
        return None
    opening, closing = span
    context = source[: opening + 1] + "<MODEL_BODY>" + source[closing:]
    if skeleton:
        context = _TODO_RE.sub("", context)
    return _SPACE_RE.sub("", context)


def _outside_target_body(source: str) -> str | None:
    span = first_function_body(source)
    if span is None:
        return None
    opening, closing = span
    return source[: opening + 1] + "<MODEL_BODY>" + source[closing:]


def _acsl_annotations(source: str) -> tuple[str, ...]:
    """Return normalized ACSL block and line annotations in source order."""
    found: list[tuple[int, str]] = []
    for match in re.finditer(r"/\*@([\s\S]*?)\*/", source):
        found.append((match.start(), _SPACE_RE.sub("", match.group(1))))
    for match in re.finditer(r"(?m)^\s*//@(.*)$", source):
        found.append((match.start(), _SPACE_RE.sub("", match.group(1))))
    return tuple(text for _, text in sorted(found))


def annotation_digest(source: str) -> str:
    payload = "\x1e".join(_acsl_annotations(source)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def check_fixed_task_integrity(candidate: str, skeleton: str) -> IntegrityResult:
    expected_outside = _outside_target_body(skeleton)
    actual_outside = _outside_target_body(candidate)
    expected_annotations = _acsl_annotations(expected_outside or "")
    actual_annotations = _acsl_annotations(actual_outside or "")
    annotations_ok = (
        bool(expected_annotations) and actual_annotations == expected_annotations
    )
    expected_context = _normalized_context(skeleton, skeleton=True)
    actual_context = _normalized_context(candidate, skeleton=False)
    context_ok = expected_context is not None and actual_context == expected_context

    reasons = []
    if not annotations_ok:
        reasons.append("ACSL annotations changed, were removed, or were added")
    if not context_ok:
        reasons.append("code outside the target function body changed")
    return IntegrityResult(
        ok=annotations_ok and context_ok,
        annotations_unchanged=annotations_ok,
        context_unchanged=context_ok,
        reason="; ".join(reasons),
    )


__all__ = [
    "IntegrityResult",
    "annotation_digest",
    "check_fixed_task_integrity",
    "first_function_body",
    "function_body_spans",
]
