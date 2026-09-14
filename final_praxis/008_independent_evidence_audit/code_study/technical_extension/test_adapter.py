"""Local self-authored routing controls; no constructor, credentials, or API calls."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from adapter import FrozenBedrockAdapter, REVIEW_JSON_SCHEMA, REVIEW_SYSTEM, StructuredReviewAdapter


def main():
    checks, captured = {}, []
    ledger = object()
    adapter = object.__new__(StructuredReviewAdapter)
    adapter.model_id = 'qwen.qwen3-coder-next'
    adapter.ledger = ledger
    messages = [{'role': 'system', 'content': REVIEW_SYSTEM}, {'role': 'user', 'content': '{"synthetic":"review"}'}]
    original = copy.deepcopy(messages)

    def capture(self, actual_messages, **kwargs):
        captured.append({'self': self, 'messages': actual_messages, **kwargs})
        return 'mock-result'

    with patch.object(FrozenBedrockAdapter, 'generate', capture):
        result = adapter.generate(messages, max_new_tokens=1024, request_id='review-synthetic', seed=7)
        row = captured[-1]
        checks['delegates_once'] = len(captured) == 1 and result == 'mock-result'
        checks['same_message_identity'] = row['messages'] is messages
        checks['same_message_content'] = messages == original
        checks['unchanged_token_cap'] = row['max_new_tokens'] == 1024
        checks['unchanged_temperature'] = row['temperature'] == 0
        checks['unchanged_seed'] = row['seed'] == 7
        checks['exact_schema'] = row['json_schema'] == REVIEW_JSON_SCHEMA
        checks['schema_is_copy'] = row['json_schema'] is not REVIEW_JSON_SCHEMA
        checks['request_v2_namespace'] = row['request_id'] == 'v2-review-synthetic'
        checks['inherited_ledger_identity'] = row['self'].ledger is ledger
        adapter.generate(messages, max_new_tokens=1024, request_id='v2-review-synthetic')
        checks['idempotent_v2_namespace'] = captured[-1]['request_id'] == 'v2-review-synthetic'
        proposal = [{'role': 'system', 'content': 'Synthetic proposal system'}, {'role': 'user', 'content': 'Synthetic proposal'}]
        adapter.generate(proposal, max_new_tokens=2048, request_id='proposal-synthetic')
        row = captured[-1]
        checks['proposal_unchanged'] = row['messages'] is proposal and row['max_new_tokens'] == 2048 and row['json_schema'] is None and row['request_id'] == 'proposal-synthetic'
        adapter.model_id = 'mistral.devstral-2-123b'
        adapter.generate(messages, max_new_tokens=1024, request_id='review-other-model')
        row = captured[-1]
        checks['other_model_unchanged'] = row['messages'] is messages and row['json_schema'] is None and row['request_id'] == 'review-other-model'
        adapter.model_id = 'qwen.qwen3-coder-next'
        for name, actual_messages, options in [
            ('reject_larger_cap', messages, {'max_new_tokens': 4096, 'request_id': 'review-fail'}),
            ('reject_nonzero_temperature', messages, {'max_new_tokens': 1024, 'temperature': 0.1, 'request_id': 'review-fail'}),
            ('reject_changed_system', proposal, {'max_new_tokens': 1024, 'request_id': 'review-fail'}),
            ('reject_wrong_request_id', messages, {'max_new_tokens': 1024, 'request_id': 'proposal-fail'}),
            ('reject_missing_request_id', messages, {'max_new_tokens': 1024}),
            ('reject_caller_schema', messages, {'max_new_tokens': 1024, 'request_id': 'review-fail', 'json_schema': REVIEW_JSON_SCHEMA}),
        ]:
            before = len(captured)
            try:
                adapter.generate(actual_messages, **options)
            except ValueError:
                checks[name] = len(captured) == before
            else:
                checks[name] = False
    receipt = {'scope': 'Self-authored metadata/routing tests with the base generate method replaced by an in-memory recorder.', 'adapter_sha256': hashlib.sha256(Path(__file__).with_name('adapter.py').read_bytes()).hexdigest(), 'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'checks_passed': sum(checks.values()), 'checks_total': len(checks), 'checks': checks, 'api_calls': 0, 'benchmark_programs_executed': False}
    print(json.dumps(receipt, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
