"""Version-two Qwen review formatting adapter; frozen v1 source stays unchanged.

Only the output schema and request-ID namespace change. Review messages, output
token cap, temperature, parsing, proposal calls, and the inherited budget ledger
are preserved. Importing this module makes no API call.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys

STUDY_ROOT = Path(__file__).resolve().parent.parent
if str(STUDY_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDY_ROOT))

from bedrock_adapter import BedrockAdapter as FrozenBedrockAdapter
from prompts import REVIEW_SYSTEM

TARGET_MODEL = 'qwen.qwen3-coder-next'
REVIEW_TOKEN_CAP = 1024
REVIEW_JSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'decision': {'type': 'string', 'enum': ['accept', 'keep']},
        'reason': {'type': 'string'},
    },
    'required': ['decision', 'reason'],
    'additionalProperties': False,
}
SCHEMA_SHA256 = hashlib.sha256(json.dumps(REVIEW_JSON_SCHEMA, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def version_two_id(request_id):
    if not isinstance(request_id, str):
        raise ValueError('The technical extension requires an explicit review request ID')
    if request_id.startswith('v2-review-'):
        return request_id
    if request_id.startswith('review-'):
        return 'v2-' + request_id
    raise ValueError('Unexpected review request-ID namespace')


class StructuredReviewAdapter(FrozenBedrockAdapter):
    """Drop-in adapter for the separately frozen technical-extension runner."""

    def generate(self, messages, max_new_tokens=512, temperature=0, *, json_schema=None,
                 request_id=None, seed=None):
        system_messages = [message.get('content') for message in messages if message.get('role') == 'system']
        review_prompt = system_messages == [REVIEW_SYSTEM]
        review_id = isinstance(request_id, str) and request_id.startswith(('review-', 'v2-review-'))
        if self.model_id == TARGET_MODEL and (review_prompt or review_id):
            if not review_prompt or not review_id:
                raise ValueError('Qwen review prompt and request-ID identity must both match')
            if max_new_tokens != REVIEW_TOKEN_CAP:
                raise ValueError('Version two preserves the 1024-token review cap')
            if temperature != 0:
                raise ValueError('Version two preserves temperature zero')
            if json_schema is not None:
                raise ValueError('The technical extension owns the exact review schema')
            return super().generate(
                messages, max_new_tokens=max_new_tokens, temperature=temperature,
                json_schema=copy.deepcopy(REVIEW_JSON_SCHEMA),
                request_id=version_two_id(request_id), seed=seed,
            )
        return super().generate(
            messages, max_new_tokens=max_new_tokens, temperature=temperature,
            json_schema=json_schema, request_id=request_id, seed=seed,
        )
