"""Loopback-only microbatch inference server for pinned local scientific models."""
import argparse
import json
import queue
import threading
import time
from collections import defaultdict
from concurrent.futures import Future
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .model_adapter import TransformersAdapter


def serve(adapter, port, batch_size):
    work_queue = queue.Queue()

    def worker():
        while True:
            batch = [work_queue.get()]
            deadline = time.monotonic() + 0.04
            while len(batch) < batch_size:
                try:
                    batch.append(work_queue.get(timeout=max(0.001, deadline-time.monotonic())))
                except queue.Empty:
                    break
            grouped = defaultdict(list)
            for payload, future in batch:
                grouped[(payload["max_new_tokens"], payload["temperature"])].append((payload, future))
            for (tokens, temperature), group in grouped.items():
                try:
                    results = adapter.generate_batch([payload["messages"] for payload, _ in group], tokens, temperature)
                    for (payload, future), result in zip(group, results):
                        result["request_id"] = payload["request_id"]
                        future.set_result(result)
                except Exception as exc:
                    for _, future in group:
                        future.set_exception(exc)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.respond(200, {"status": "ready", "runtime": adapter.runtime, "batch_limit": batch_size})

        def do_POST(self):
            try:
                if self.path != "/generate":
                    raise ValueError("Unknown endpoint")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 500000:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(size))
                if payload["model_id"] != adapter.model_id or payload["revision"] != adapter.revision:
                    raise ValueError("Frozen model identity mismatch")
                future = Future()
                work_queue.put((payload, future))
                self.respond(200, future.result(timeout=840))
            except Exception as exc:
                self.respond(500, {"error": type(exc).__name__, "detail": str(exc)})

    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(json.dumps({"status": "ready", "port": port, "runtime": adapter.runtime}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model-id", required=True)
    p.add_argument("--revision", required=True)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--batch-size", type=int, default=8)
    args = p.parse_args()
    serve(TransformersAdapter(args.model_id, args.revision), args.port, args.batch_size)
