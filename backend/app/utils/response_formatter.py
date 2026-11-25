"""Format model output into typed endpoint response fields."""

import re
from collections.abc import Mapping, Sequence

_HEADING = re.compile(r"(?m)^#{1,3}\s+(.+?)\s*$")
_CODE_FENCE = re.compile(r"```[^\r\n]*\r?\n(.*?)```", re.DOTALL)


def _normalize_heading(heading: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", heading.casefold()).strip()


def extract_sections(response: str, aliases: Mapping[str, Sequence[str]]) -> dict[str, str]:
    """Extract named Markdown sections, returning empty strings if absent."""
    matches = list(_HEADING.finditer(response))
    sections: dict[str, str] = {key: "" for key in aliases}
    normalized_aliases = {
        _normalize_heading(alias): key
        for key, names in aliases.items()
        for alias in names
    }
    for index, match in enumerate(matches):
        key = normalized_aliases.get(_normalize_heading(match.group(1)))
        if key is None:
            continue
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(response)
        sections[key] = response[content_start:content_end].strip()
    return sections


def extract_code(section: str, fallback: str) -> str:
    """Remove a Markdown code fence, or use the response when none was emitted."""
    match = _CODE_FENCE.search(section)
    if match:
        return match.group(1).strip()
    return section.strip() or fallback.strip()


def split_bullets(section: str) -> list[str]:
    """Convert a model-generated list or paragraph to a non-empty list."""
    items = [
        re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", line).strip()
        for line in section.splitlines()
    ]
    items = [item for item in items if item]
    if items:
        return items
    return [section.strip()] if section.strip() else []
