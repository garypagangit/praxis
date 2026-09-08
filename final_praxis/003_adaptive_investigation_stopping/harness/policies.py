"""Frozen policies receive only exposed dispositions and public risk metadata."""
try:
    from .review_gate import reasons
except ImportError:
    from review_gate import reasons

ARMS = ("A0", "A1", "A2", "A4")

def select(case, trace, arm):
    observations, decisions, reviewed = [], [], False
    selected, final = 8, "abstain"
    for r, row in enumerate(trace, 1):
        observations.append(row["disposition"])
        stable = r >= 2 and observations[-1] == observations[-2] and observations[-1] != "abstain"
        triggers = reasons(case, observations) if arm == "A4" and r >= 2 else []
        if arm == "A0":
            action = "STOP" if r == 2 else "CONTINUE"
        elif arm == "A1":
            action = "STOP" if r == 8 else "CONTINUE"
        elif arm == "A2":
            action = "STOP" if stable or r == 8 else "CONTINUE"
        elif arm == "A4":
            action = "REVIEW" if triggers else "STOP" if stable or r == 8 else "CONTINUE"
        else:
            raise ValueError(arm)
        reviewed |= action == "REVIEW"
        decisions.append({"round": r, "action": action, "reasons": triggers})
        if action == "STOP" or r == 8:
            selected = r
            final = "abstain" if action == "REVIEW" else row["disposition"]
            break
    return {"arm": arm, "round": selected, "disposition": final, "reviewed": reviewed,
            "abstained": final == "abstain", "decisions": decisions,
            "token_count": sum(row["token_count"] for row in trace[:selected])}
