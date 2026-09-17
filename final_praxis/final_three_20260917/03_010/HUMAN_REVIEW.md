# Human understanding and scope review: 010 D0

**Current status: UNREVIEWED BY HUMAN AUTHOR/COMMITTEE.** The completed experiment and computational audits are preserved. This worksheet does not create or imply an approval. The manuscript is AI-assisted and requires the named human author's own understanding, review, and responsibility before submission.

## Evidence walkthrough

Complete these prompts using the [evidence map](EVIDENCE.json), [paper](PAPER.md), and linked original artifacts. Record explanations in your own words.

1. **State the question precisely.** Explain why forecast displacement and increased forecast error are different endpoints. Identify which one failed its registered aggregate condition.
2. **Reconstruct one observation.** For raw joint forecasting, Ramp 6, origin index 20 (original time index 785), locate the clean forecast, perturbed forecast, and unchanged target in the saved arrays. Recalculate the mean error change across channels 1 and 2: 0.12704186141490936. Explain why that harmful example is compatible with a negative all-origin mean.
3. **Explain the denominator.** Derive the 32-context mean and 64-scalar-target clean MAE. Explain why conditioning either on high-displacement contexts would answer a different question.
4. **Explain the gate.** State the 0.05 displacement threshold, minimum eight contexts, 0.02 mean-error threshold, and minimum two variants. Use Table 1 to show why five passing displacement counts still yield zero qualifying variants.
5. **Interpret the simple controls.** Explain why `adequate_simple_controls=[]` means the conditional investment gate was not reached. Identify one positive mean-change cell in each preprocessing pipeline without converting it into a replacement raw-joint hypothesis.
6. **Trace model routes.** Show the explicit joint/independent settings and native-call evidence. Derive 1,024 evaluations, 1,536 forward calls, and 3,072 scalar channel sequences. Explain why these are not three alternative sample sizes.
7. **Trace numerical controls.** Explain the point-based numerical floor and separate quantile-repeat check. State what the observed zeros support and what they cannot establish about other hardware or data.
8. **Trace chronology.** Locate the frozen protocol, specification, runtime freeze, and source commit, followed by the completed outcome. Explain why unchanged historical plan-only labels do not indicate an unrun experiment.

## Contribution and scope decisions

- Describe the contribution without claiming a new detector, new defense, first use of context gating, or safety guarantee.
- Compare D0 with the three primary papers in [PRIOR_WORK.md](PRIOR_WORK.md). Explain why fixed SMA-5 is not the complete GITCO method and why D0 reports no conformal alarm-control result.
- Explain how one previously inspected univariate series became three artificial channels. Identify the experimental meaning of “protected”; do not substitute real hardware trust or measured sensor independence.
- Explain why overlapping origins and paired variants do not establish independent incident replication. State why no confidence interval assuming independent windows appears.
- Confirm that the six negative raw-joint means coexist with individual harmful cases and do not prove universal robustness.
- Confirm that the current decision is to close D0 and hold D1 scale-up; no new experiment is needed to make this completed report accurately describe its result.
- Review the existing data notices and pinned model-weight terms before any redistribution or submission.
- Distinguish the conservative $0.1734 compute estimate from an invoice and the $5 allowance from recorded spending.

## Record a real review when it occurs

| Field | Current entry |
|---|---|
| Human reviewer / role | Not recorded |
| Review date | Not recorded |
| Paired numerical example reproduced by reviewer | Not recorded |
| Originality and applied-contribution assessment | Not recorded |
| Program-specific acceptability of this negative report | Not recorded |
| Authorship and AI-assistance disclosure reviewed | Not recorded |
| Claims requiring revision | Not recorded |
| Submission or committee approval | Not recorded |

These entries deliberately remain unfilled. Computational audit PASS does not answer them. Human review may accept the bounded report, request a specific correction, or judge that it is unsuitable as a primary Praxis; none of those outcomes has been fabricated here.
