"""Design constants, fixed before the lateral-protection development fits."""
from copy import deepcopy
from ..tabular_followup.run_strong_baselines import GRIDS

def design():
    return {
        "schema_version": 1, "experiment": "LATERAL_PROTECTION_DEVELOPMENT_V1",
        "status": "FROZEN_BEFORE_NEW_MODEL_FITS", "study_kind": "exposed_source_development",
        "data_npz_sha256": "8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565",
        "manifest_sha256": "772edbce9548a1dc87a0e9dd835f9002dfd5a2bb7b3cc37de212d7b3c43791e3",
        "e1_protocol_sha256": "9d4c69f9ab8af48dae44aae6c237a25cedc56a1f50eff819513fa2e9beb7c687",
        "models": ["xgboost", "lightgbm"], "schemes": ["natural", "balanced", "lateral2", "lateral4"],
        "model_grids": {"xgboost": deepcopy(GRIDS["xgboost"]), "lightgbm": deepcopy(GRIDS["lightgbm"][:9])},
        "groups": [{"budget": 1024, "seed": s} for s in range(20260921, 20260931)] +
                  [{"budget": b, "seed": s} for b in [32, 128, 512] for s in range(20260921, 20260924)],
        "samples_per_attack_class": 32, "n_splits": 3, "cpu_threads": 4,
        "support_rule": "Original E1 32/class support plus first budget-32 rows of original strong-control hashed benign extension",
        "partition_tag": "LATERAL_SELECTION_20260921",
        "partition_rule": "Within each old calibration class sort SHA256(tag|fingerprint); first floor(n/2) selection, rest verification; original test descriptive only",
        "score": "1-p(NormalTraffic)", "alert_rule": "score > threshold; equal scores never split",
        "selection_reference": "Maximum lateral TP under FPR<=.01 and lateral recall>=.90; ties minimum FP, frozen cell order, maximum threshold",
        "selection_candidate": "Minimum FP under FPR<=.01 and recall>=max(.90, reference recall-.03); ties maximum lateral TP, frozen cell order, maximum threshold",
        "threshold_only_ablation": "Same candidate objective and constraints on locked reference detector only",
        "ordinary_controls": "Fit-CV-best natural detector, argmax plus selection-normal-only empirical 1% threshold; not an NP confidence certificate",
        "verification_gate": {"all_10_primary_seeds_feasible": True, "mean_seed_fpr_relative_reduction_strictly_greater": .20,
            "mean_seed_lateral_loss_strictly_less_than": .03, "mean_seed_lateral_recall_min": .90, "mean_seed_fpr_max": .01},
        "secondary": "All smaller budgets at first three seeds; all per-cell argmax/stage metrics; no outcome-dependent budget selection",
        "failure": "Keep every infeasible seed; no retuning or fallback on verification/test; no confirmation or statistical guarantee from development point estimates",
        "resources": "Two concurrent group workers maximum, four CPU threads each. Trees only; no unmatched foundation-model claim.",
        "label_accounting": "Fit=160+budget; selection/verification/test labels separately counted. Reused labels and overlapping seeds do not create independent incidents.",
    }
