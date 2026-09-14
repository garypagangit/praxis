# CTI development: evidence navigation and human-authorship handoff

**Internal AI-assisted aid. Not approved for academic submission.** The current [GW doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links an [AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) restricting AI-written and AI-edited submitted academic work. No applicable written exception was found. Human editing alone is not a demonstrated remedy. These documents preserve their AI provenance; they are not a ready-to-submit Praxis.

- [Internal evidence and development guide](INTERNAL_RESEARCH_GUIDE.md), [Word](INTERNAL_RESEARCH_GUIDE.docx), [PDF](INTERNAL_RESEARCH_GUIDE.pdf).
- [Machine-readable evidence index](EVIDENCE_INDEX.json) and [consistency-check receipt](CONSISTENCY_CHECK.json).
- [Official-source retrieval record](REQUIREMENTS_SOURCES.json), including the 2026 template and policy hashes. Retrieval on September 14, 2026 does not establish the AI policy's effective date.
- [Completed, immutable CTI paper and evidence](../papers/20260914/01_cti/README.md). This package adds no model calls and changes none of those results.

The guide maps the source-compatible gains, mismatch harm, failed PX068 routing confirmation and unfinished PX071 to their evidence. It provides questions for the author's independent preparation and a clearly unrun candidate extension if a stronger process contribution is required. Doctoral originality and authorization remain academic determinations.

Run the local checks from this directory:

```powershell
python check_consistency.py
python -m unittest test_consistency.py
```

The verification code was developed with Codex assistance. It verifies exact archived values and source hashes, not academic acceptance or scientific novelty. The author must understand the code and make the required attribution for any academic use. `build_evidence.py` recreates the JSON index from the published source analyses. No network or inference is needed for these operations.

To rebuild the visual guide, use `build_guide.py --source INTERNAL_RESEARCH_GUIDE.md --label "CTI - INTERNAL RESEARCH AID" --output-dir . --work-dir <local-render-directory>`. This requires Python document dependencies, LibreOffice and Microsoft's MML2OMML stylesheet; it is document rendering only. Every delivered PDF page was visually inspected, with artifact hashes in [VISUAL_QA.json](VISUAL_QA.json). The [manifest](MANIFEST.json) inventories release files.

The existing 20-page empirical manuscript is not a full approximately 80-page Praxis body. The immediate useful work is independent source reading, code understanding and an author-created research argument, together with verifying any applicable written authorization before submitted writing. No email or submission has been sent.
