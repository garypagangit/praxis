#!/usr/bin/env python3
"""AIVH runner.

Examples
--------
# smoke test on synthetic data (no download needed)
python scripts/run.py --synthetic --out results/synthetic

# build the corpus from the real Zenodo dump + your human JSONL, then evaluate
python scripts/run.py --zenodo data/zenodo --human data/human/*.cast --out results/real
"""
import argparse
import glob
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aivh import ingest, evaluate, synth  # noqa: E402


def build_corpus(args):
    sessions = []
    if args.zenodo:
        print(f"[ingest] zenodo from {args.zenodo}")
        sessions += list(ingest.load_zenodo(Path(args.zenodo)))
    for pat in args.human or []:
        for p in glob.glob(pat):
            s = ingest.load_asciinema(Path(p))
            if s:
                sessions.append(s)
    for pat in args.cowrie or []:
        for p in glob.glob(pat):
            sessions += list(ingest.load_cowrie(Path(p), label_fn=ingest.default_cowrie_label))
    return sessions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--zenodo")
    ap.add_argument("--human", nargs="*")
    ap.add_argument("--cowrie", nargs="*")
    ap.add_argument("--out", default="results/run")
    ap.add_argument("--kind", default="gbm", choices=["gbm", "logreg"])
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.synthetic:
        print("[synth] generating synthetic corpus (stub priors, NOT real data)")
        sessions = synth.generate(seed=args.seed)
    else:
        sessions = build_corpus(args)

    print(f"[corpus] {len(sessions)} sessions")
    from collections import Counter
    print(f"[corpus] labels: {dict(Counter(s.label for s in sessions))}")
    print(f"[corpus] families: {dict(Counter(s.model_family for s in sessions))}")

    rep = evaluate.full_suite(sessions, args.out, kind=args.kind, alpha=args.alpha, seed=args.seed)

    def line(tag, r):
        if r is None:
            return f"  {tag:28s}  (skipped)"
        ma = r.get("mean_auroc")
        extra = ""
        if "gate_mean_coverage" in r:
            extra = f"  gate cov={r['gate_mean_coverage']}  decided_err={r['gate_mean_decided_error']}"
        mn = f"  min={r['min_auroc']}" if r.get("min_auroc") is not None else ""
        return f"  {tag:28s}  mean AUROC={ma}{mn}{extra}"

    print("\n=== PX-090 AIVH results ===")
    print(line("RQ1 random k-fold", rep["RQ1_random"]))
    print(line("RQ4 timing-free (C+S+E)", rep["RQ4_timing_free"]))
    print(line("RQ4 timing-only (T)", rep["RQ4_timing_only"]))
    print(line("RQ2 leave-one-LLM-family-out", rep["RQ2_LOLO"]))
    print(line("RQ2 LOLO timing-free", rep["RQ2_LOLO_timing_free"]))
    print(line("RQ3 leave-one-env-out", rep["RQ3_LOEO"]))
    print(f"\n[out] wrote {args.out}/report_{args.kind}.json")

    if "feature_importance" in rep:
        print("\n  top features (permutation importance):")
        for row in rep["feature_importance"][:10]:
            print(f"    {row['feature']:28s} {row['importance']:.4f}")


if __name__ == "__main__":
    main()
