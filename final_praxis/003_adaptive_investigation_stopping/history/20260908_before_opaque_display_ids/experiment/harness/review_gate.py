"""Mechanical review, independent of hidden labels and correctness."""
def reasons(case, observed):
    r = len(observed)
    result = []
    if case["protected_high_impact"]:
        result.append("protected_high_impact")
    if r < case["minimum_review_round"]:
        result.append("low_evidence_completeness")
    if r >= 2 and observed[-1] != observed[-2]:
        result.append("latest_disposition_flip")
    if observed[-1] == "abstain":
        result.append("abstention")
    return result
