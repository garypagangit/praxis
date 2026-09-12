"""Real Bedrock inference with raw receipts, explicit retries, and a shared budget.

Only text/schema inference is exposed. Model output is never executed. Exact AWS
model IDs are recorded; managed backend weights are not represented as hash-pinned.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent
RATES = {
    "qwen.qwen3-coder-next": (0.50, 1.20),
    "mistral.devstral-2-123b": (0.40, 2.00),
    "deepseek.v3.2": (0.62, 1.85),
}
PRICE_SOURCE = "https://aws.amazon.com/bedrock/pricing/"
PRICE_CHECKED = "2026-09-12"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_default(value):
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=json_default)


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical(value) + "\n")


class BudgetExceeded(RuntimeError):
    pass


class BudgetLedger:
    """File-backed budget shared by models/processes; unresolved attempts stay reserved."""

    def __init__(self, path=None, limit_usd=15.0):
        self.path = Path(path or ROOT / "execution" / "development_budget.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit_usd = float(limit_usd)
        if not 0 < self.limit_usd <= 100:
            raise ValueError("Pilot inference ledger must be within $100")
        self.lock_path = self.path.with_suffix(".lock")
        with self.locked():
            if not self.path.exists():
                self._save({"schema": "enhanced-bedrock-budget-v1", "limit_usd": self.limit_usd,
                            "entries": {}, "price_source": PRICE_SOURCE,
                            "price_checked": PRICE_CHECKED, "invoice_claimed": False})
            elif self._read()["limit_usd"] != self.limit_usd:
                raise ValueError("Existing budget limit differs; use a separately named ledger")

    @contextmanager
    def locked(self):
        # OS locks release when a process exits, including connectivity-independent
        # process crashes; no stale O_EXCL lock can strand the budget ledger.
        with self.lock_path.open("a+b") as handle:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"0"); handle.flush()
            deadline = time.monotonic() + 30
            while True:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Budget ledger remains locked")
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state):
        temporary = self.path.with_name(self.path.name + "." + uuid.uuid4().hex + ".tmp")
        temporary.write_text(canonical(state) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def reserve(self, attempt_id, amount, model_id):
        with self.locked():
            state = self._read()
            if attempt_id in state["entries"]:
                raise ValueError("Duplicate attempt ID")
            total = sum(row["accounted_usd"] for row in state["entries"].values())
            if total + amount > state["limit_usd"]:
                raise BudgetExceeded(f"Budget would exceed ${state['limit_usd']:.2f}")
            state["entries"][attempt_id] = {
                "model_id": model_id, "reserved_usd": amount, "accounted_usd": amount,
                "status": "RESERVED", "created_utc": utc_now()}
            self._save(state)

    def settle(self, attempt_id, amount=None, status="SUCCESS", usage=None):
        with self.locked():
            state = self._read()
            row = state["entries"][attempt_id]
            if amount is not None:
                row["accounted_usd"] = amount
            row.update(status=status, completed_utc=utc_now(), usage=usage)
            self._save(state)


class BedrockAdapter:
    def __init__(self, model_id, *, profile="praxis-build", region="us-east-1",
                 receipt_dir=None, ledger=None, max_attempts=3, timeout=300,
                 additional_model_request_fields=None, client=None):
        if model_id not in RATES:
            raise ValueError("Model requires a verified price entry before invocation")
        if region != "us-east-1":
            raise ValueError("These verified prices and execution scope use us-east-1")
        if not 1 <= max_attempts <= 3:
            raise ValueError("One to three explicit attempts are supported")
        prereg_path = os.environ.get("PRAXIS_PREREG_PATH")
        prereg_hash = os.environ.get("PRAXIS_PREREG_SHA256")
        if not prereg_path or not prereg_hash:
            raise ValueError("A frozen, hashed preregistration is required before inference")
        if hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest() != prereg_hash:
            raise ValueError("Preregistration bytes changed after freeze")
        self.prereg_hash = prereg_hash
        self.model_id, self.region = model_id, region
        self.receipt_dir = Path(receipt_dir or ROOT / "execution" / "raw_inference")
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger or BudgetLedger()
        self.max_attempts = max_attempts
        self.additional = additional_model_request_fields
        # Disable hidden SDK retries: every actual attempt must have its own receipt.
        self.client = client or boto3.Session(profile_name=profile, region_name=region).client(
            "bedrock-runtime", config=Config(connect_timeout=15, read_timeout=timeout,
                                             retries={"total_max_attempts": 1},
                                             max_pool_connections=16))

    def request(self, prompt, system="", max_tokens=512, seed=None, *,
                json_schema=None, request_id=None, temperature=0):
        messages = ([{"role": "system", "content": system}] if system else [])
        messages.append({"role": "user", "content": prompt})
        return self.generate(messages, max_new_tokens=max_tokens, temperature=temperature,
                             json_schema=json_schema, request_id=request_id, seed=seed)

    def generate(self, messages, max_new_tokens=512, temperature=0, *, json_schema=None,
                 request_id=None, seed=None):
        if not 1 <= max_new_tokens <= 4096:
            raise ValueError("Output token bound must be 1..4096")
        if temperature != 0:
            raise ValueError("This experiment adapter freezes temperature=0")
        request_id = request_id or uuid.uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}", request_id):
            raise ValueError("Unsafe or oversized request ID")
        body = {"modelId": self.model_id, "messages": [],
                "inferenceConfig": {"maxTokens": max_new_tokens, "temperature": temperature},
                "requestMetadata": {"experiment": "final-praxis-004-007-20260912",
                                    "request_id": request_id, "preregistration_sha256": self.prereg_hash}}
        system = []
        for message in messages:
            if set(message) != {"role", "content"} or not isinstance(message["content"], str):
                raise ValueError("Only role/content text messages are supported")
            if message["role"] == "system":
                system.append({"text": message["content"]})
            elif message["role"] in {"user", "assistant"}:
                body["messages"].append({"role": message["role"],
                                         "content": [{"text": message["content"]}]})
            else:
                raise ValueError("Unsupported role")
        if not body["messages"]:
            raise ValueError("At least one user message is required")
        if system:
            body["system"] = system
        if self.additional:
            body["additionalModelRequestFields"] = self.additional
        if json_schema is not None:
            body["outputConfig"] = {"textFormat": {"type": "json_schema", "structure": {
                "jsonSchema": {"name": "experiment_response", "schema": canonical(json_schema)}}}}
        prompt_hash = hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()
        # Stable across request IDs, while prompt_sha256 preserves the complete
        # request-body hash used by the initial access receipts.
        content_hash = hashlib.sha256(canonical({k: v for k, v in body.items()
                                                if k != "requestMetadata"}).encode("utf-8")).hexdigest()
        cached = self.receipt_dir / (request_id + ".result.json")
        if cached.exists():
            prior = json.loads(cached.read_text(encoding="utf-8"))
            if prior["inference_input_sha256"] != content_hash:
                raise ValueError("Request ID reused for different inference content")
            if prior.get("preregistration_sha256") != self.prereg_hash:
                raise ValueError("Cached result belongs to a different preregistration")
            return dict(prior, recovered_from_cache=True)
        input_rate, output_rate = RATES[self.model_id]
        # Serialized UTF-8 bytes plus template allowance provide a conservative
        # reservation, not a reported token count. Actual counters come from AWS.
        reservation = ((len(canonical(body).encode("utf-8")) + 1024) * input_rate
                       + max_new_tokens * output_rate) / 1_000_000
        call_started = time.monotonic()
        unresolved_cost_reservation = 0.0
        for attempt in range(1, self.max_attempts + 1):
            attempt_id = f"{request_id}.attempt-{attempt}"
            request_path = self.receipt_dir / (attempt_id + ".request.json")
            write_new(request_path, {"schema": "enhanced-bedrock-request-v1", "request": body,
                                     "request_id": request_id, "attempt": attempt,
                                     "timestamp_utc": utc_now(), "seed_requested": seed,
                                     "seed_supported": False, "prompt_sha256": prompt_hash,
                                     "inference_input_sha256": content_hash})
            self.ledger.reserve(attempt_id, reservation, self.model_id)
            started = time.monotonic()
            try:
                raw = self.client.converse(**body)
            except Exception as error:
                code = (error.response.get("Error", {}).get("Code", type(error).__name__)
                        if isinstance(error, ClientError) else type(error).__name__)
                write_new(self.receipt_dir / (attempt_id + ".error.json"), {
                    "request_id": request_id, "attempt": attempt, "error_type": code,
                    "timestamp_utc": utc_now(), "seconds": time.monotonic() - started,
                    "detail": str(error), "possible_billing_reserved": reservation})
                # A rejected request is not generation; network/server failures may
                # have reached inference and keep their conservative reservation.
                rejected = code in {"AccessDeniedException", "ValidationException",
                                    "ResourceNotFoundException", "ThrottlingException"}
                self.ledger.settle(attempt_id, 0.0 if rejected else None, "ERROR_" + code)
                if not rejected:
                    unresolved_cost_reservation += reservation
                retryable = code in {"ThrottlingException", "ServiceUnavailableException",
                                     "ModelNotReadyException", "InternalServerException"}
                if not retryable or attempt == self.max_attempts:
                    raise
                time.sleep(min(2 ** attempt, 8))
                continue
            seconds = time.monotonic() - started
            write_new(self.receipt_dir / (attempt_id + ".response.json"), raw)
            usage = raw.get("usage", {})
            if not all(isinstance(usage.get(k), int) for k in ("inputTokens", "outputTokens")):
                self.ledger.settle(attempt_id, status="MISSING_USAGE")
                raise RuntimeError("AWS token counters absent; response retained")
            cost = (usage["inputTokens"] * input_rate + usage["outputTokens"] * output_rate) / 1_000_000
            self.ledger.settle(attempt_id, cost, usage=usage)
            content = raw.get("output", {}).get("message", {}).get("content", [])
            text = "".join(block["text"] for block in content if "text" in block)
            result = {
                "text": text, "model_id": self.model_id, "revision": self.model_id,
                "backend_weights_pinned": False, "region": self.region,
                "request_id": request_id,
                "aws_request_id": raw.get("ResponseMetadata", {}).get("RequestId"),
                "prompt_tokens": usage["inputTokens"], "completion_tokens": usage["outputTokens"],
                "input_tokens": usage["inputTokens"], "output_tokens": usage["outputTokens"],
                "usage": usage, "finish_reason": raw.get("stopReason"),
                "cost_usd_estimate": cost, "price_source": PRICE_SOURCE,
                "price_checked": PRICE_CHECKED,
                "unresolved_cost_reservation_usd": unresolved_cost_reservation,
                "accounted_usd_estimate": cost + unresolved_cost_reservation,
                "timestamp_utc": utc_now(), "seconds": time.monotonic() - call_started,
                "successful_attempt_seconds": seconds, "attempts": attempt,
                "prompt_sha256": prompt_hash, "inference_input_sha256": content_hash,
                "seed_requested": seed, "seed_supported": False,
                "request_receipt": str(request_path),
                "response_receipt": str(self.receipt_dir / (attempt_id + ".response.json")),
                "preregistration_sha256": self.prereg_hash,
                "runtime": {"provider": "Amazon Bedrock", "api": "Converse",
                            "boto3": boto3.__version__, "structured_output": json_schema is not None},
            }
            write_new(self.receipt_dir / (request_id + ".result.json"), result)
            return result
        raise AssertionError("Unreachable retry state")

