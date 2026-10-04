# Primary Praxis — October 4, 2026 review edition

**When Better APT Scores Hide Missed Attack Warnings**

- [Praxis PDF](delivery/Gary_Pagan_Praxis_Review.pdf)
- [Editable Word manuscript](delivery/Gary_Pagan_Praxis_Review.docx)
- [One-page executive summary](delivery/Executive_Summary.pdf)
- [Academic and AI-use review assessment](REVIEW_READINESS.md)
- [PX-106 results](../warning_transitions_20261004/FINDINGS.md)

This edition revises the original five-chapter Praxis as an applied auditable-AI study. It follows the structure of the two user-supplied GWU examples, simplifies the research framing, preserves the historical result tables and equations, integrates PX-098 through PX-105, and adds PX-106.

PX-106 finds that a previously wrong attack-stage label can become benign and remove a warning without becoming an exact-class negative flip. Binary regression accounting captures the change. All 27 saved comparisons are reported. The complete trace and ranking follow-ups did not beat their simple controls, and their negative results remain in the paper.

The manuscript does not claim a new XAI algorithm, first discovery of model regression, actual analyst benefit or universal exfiltration detection. It includes substantive AI-assistance disclosure. This is an author/committee review edition; permission for AI-assisted submission, contribution sufficiency and formal approval remain institutional decisions.

## Rebuild

From the repository root, use the recorded Praxis Python environment:

1. `python experiments/praxis_next/gwu_revision_20261004/revise.py`
2. `python experiments/praxis_next/gwu_revision_20261004/build.py`
3. `python experiments/praxis_next/gwu_revision_20261004/check.py`
4. Inspect rendered pages and update the review receipt.
5. `python experiments/praxis_next/gwu_revision_20261004/package.py`

The renderer uses the existing repository renderer, LibreOffice/UNO and the prior equation-accessibility definitions. Original references and all historical Chapter 4 content are preserved. CONTENT_QA.json records machine checks; VISUAL_REVIEW.json describes the actual visual review. Source hashes and deliverable hashes are saved in FINAL_MANIFEST.json. Rebuilding document artifacts is separate from refitting the underlying models.
