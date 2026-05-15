# Praxis 06 Defense Slides

Generated: 2026-05-14

## Open First

- `PRAXIS06_DEFENSE_SLIDES_20260514.pptx` - usable 12-slide PowerPoint deck.
- `PRAXIS06_DEFENSE_SLIDE_OUTLINE_20260514.md` - editable slide-by-slide outline with speaker intent and backup-slide plan.
- `PRAXIS06_DEFENSE_SPEAKER_NOTES_20260514.md` - rehearsal-ready talk track, timing, and likely committee Q&A.

## Rebuild

From the repository root:

```powershell
.\.venv-diag\Scripts\python.exe scripts\build_praxis06_defense_deck.py
```

The generator reads the current Praxis 06 paper figures from `reports/tta_streaming_apt/paper_assets_20260509/figures/` when they are present and writes the PPTX back into this directory.

## Deck Claim

The defense story is intentionally narrow: selective no-label test-time adaptation recovers rare Reconnaissance-stage detection under held-out source-file shift while preserving Data Exfiltration safety under a locked validation-selected gate.
