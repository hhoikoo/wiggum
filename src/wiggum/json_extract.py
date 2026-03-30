"""Extract fenced JSON blocks from claude stdout."""

import json
import re
from typing import Any, cast

_FENCED_JSON_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def extract_last_fenced_json(text: str) -> dict[str, Any] | None:
    """Return the parsed JSON dict from the last fenced ``json`` block in *text*.

    Returns ``None`` when no fenced block is found or the JSON is malformed.
    """
    matches = _FENCED_JSON_RE.findall(text)
    if not matches:
        return None
    try:
        parsed: object = json.loads(matches[-1])
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast("dict[str, Any]", parsed)
