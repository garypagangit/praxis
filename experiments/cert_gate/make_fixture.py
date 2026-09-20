"""Write deliberately artificial scored records for offline plumbing checks."""
import argparse
import json
from pathlib import Path

import numpy as np

from replay import FIXTURE_SCOPE


def fixture():
    rng = np.random.default_rng(20260920)
    records = []
    for role, n_attack, n_benign in (("calibration", 300, 100), ("test", 100, 100)):
        for attack, count in ((True, n_attack), (False, n_benign)):
            for i in range(count):
                identifier = f"artificial-{role}-{int(attack)}-{i}"
                records.append({"record_id": identifier, "group_id": identifier, "role": role,
                                "attack": attack, "benignness": float(rng.uniform()),
                                "eligible": bool(rng.uniform() < .75)})
    return {"scope": FIXTURE_SCOPE,
            "scorer_contract": {"kind": "uniform_random_generator", "seed": 20260920,
                                "no_real_model_or_alert": True},
            "predicate_contract": {"kind": "independent_artificial_bernoulli", "probability": .75,
                                   "not_operational_predicates": True},
            "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    path = parser.parse_args().output
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(fixture(), stream, indent=2, allow_nan=False)
        stream.write("\n")
