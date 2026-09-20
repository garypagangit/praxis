"""Deterministic, label-blind content groups for exploratory SecAlertBench splits.

Grouping never modifies the text supplied to the scorer. The normalized key
starts with serialize_features() and replaces IPv4-looking substrings only when
ipaddress.IPv4Address validates all four octets. This is a conservative duplicate
diagnostic: a version string such as 1.2.3.4 is also a valid IPv4 spelling and may
be merged. Equality of these keys does not establish an independent incident.
"""
import hashlib
import ipaddress
import re

if __package__:
    from .scorers import serialize_features
else:
    from scorers import serialize_features


GROUPING_VERSION = "serialized-features-valid-ipv4-v1"
# Dot/digit boundaries prevent matching a four-octet substring inside a longer
# dot-separated numeric sequence. Other adjacent characters are allowed, so
# addresses embedded in URLs, headers, or version-like text are grouped too.
IPV4_PATTERN = r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
IPV4_PLACEHOLDER = "<ipv4>"
_IPV4_RE = re.compile(IPV4_PATTERN)


def _replace_valid_ipv4(match):
    candidate = match.group(0)
    try:
        ipaddress.IPv4Address(candidate)
    except ipaddress.AddressValueError:
        return candidate
    return IPV4_PLACEHOLDER


def exact_feature_sha(alert):
    """SHA-256 of the exact UTF-8 model serialization, excluding derived labels."""
    return hashlib.sha256(serialize_features(alert).encode("utf-8")).hexdigest()


def feature_group_sha(alert):
    """SHA-256 after grouping-only IPv4 replacement; all other text is retained.

    There is no lowercasing, whitespace rewrite, port masking, hostname masking,
    IPv6 masking, label lookup, or fitted transformation in this version.
    """
    normalized = _IPV4_RE.sub(_replace_valid_ipv4, serialize_features(alert))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
