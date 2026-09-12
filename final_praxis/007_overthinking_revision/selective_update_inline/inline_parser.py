"""Pre-test formatting amendment for Praxis007; no model, dataset, or gold access.

Only marker boundary expands: a unique exact terminal FINAL: TRUE/FALSE may
follow any whitespace, instead of requiring start-of-text or a newline.
Existing terminal wrapper whitelist and one whole-JSON-string decode are kept.
The caller must supply the unchanged original truncation decision.
"""
from __future__ import annotations
import json
import re

LABELS = ("TRUE", "FALSE")
PLAIN = r"FINAL: (?:TRUE|FALSE)"
# Exactly the wrapper combinations accepted by the prior format normalization.
WRAPPERS = (
    (r"\*\*("+PLAIN+r")\*\*", ("bold",)),
    (r"`("+PLAIN+r")`", ("backtick",)),
    (r"``("+PLAIN+r")``", ("double_backtick",)),
    (r"\*\*`("+PLAIN+r")`\*\*", ("bold", "backtick")),
    (r"\*\*``("+PLAIN+r")``\*\*", ("bold", "double_backtick")),
    (r"`\*\*("+PLAIN+r")\*\*`", ("backtick", "bold")),
    (r"``\*\*("+PLAIN+r")\*\*``", ("double_backtick", "bold")),
)

def parse_inline_terminal(text: str, *, truncated: bool = False) -> dict:
    """Return an answer plus an auditable formatting trace; never infer an answer."""
    raw_text = text
    changes = []
    result = {"answer": None, "normalized_text": text, "normalization": changes,
              "boundary": None, "invalid_reason": None}
    if not isinstance(text, str):
        result["invalid_reason"] = "non_string_text"
        return result
    # Preserve the truncation criterion from the original scorer, including token fallback.
    if truncated:
        result["invalid_reason"] = "truncated"
        return result
    try:
        decoded = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        decoded = None
    if isinstance(decoded, str):
        text = decoded
        changes.append("json_string_decoded_once")
    result["normalized_text"] = text
    # Count even differently cased/spaced markers as potential ambiguity, as before.
    if len(re.findall(r"FINAL\s*:", text, flags=re.I)) != 1:
        result["invalid_reason"] = "missing_or_multiple_markers"
        return result
    patterns = WRAPPERS + (("("+PLAIN+")", ()),)
    for pattern, wrappers in patterns:
        match = re.search(r"(?:^|\s)(?P<terminal>"+pattern+r")\s*\Z", text)
        if match is None:
            continue
        terminal_start, terminal_end = match.span("terminal")
        marker = match.group(2)
        boundary = "start" if terminal_start == 0 else (
            "newline" if text[terminal_start-1] == "\n" else "whitespace")
        result["boundary"] = boundary
        result["answer"] = marker.split(": ", 1)[1]
        result["normalized_text"] = text[:terminal_start]+marker+text[terminal_end:]
        changes.extend("terminal_"+wrapper for wrapper in wrappers)
        if boundary == "whitespace":
            changes.append("terminal_whitespace_boundary")
        return result
    result["invalid_reason"] = "not_exact_terminal_marker_with_allowed_boundary"
    return result

def rescore_inline_terminal(text: str, original_score: dict) -> dict:
    """Keep all old score fields and truncation; attach original answer and new trace.

    original_score should be recomputed by the frozen original scorer from the
    immutable raw provider response, and checked against its saved score first.
    """
    if type(original_score.get("truncated")) is not bool:
        raise ValueError("Require the original boolean truncation decision")
    new = parse_inline_terminal(text, truncated=original_score["truncated"])
    answer = dict(original_score)
    answer["original_answer"] = original_score.get("answer")
    answer.update(new)
    answer["parser_amendment"] = "007-inline-terminal-whitespace-v1"
    return answer

