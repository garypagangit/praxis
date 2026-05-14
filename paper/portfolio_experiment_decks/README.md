# Portfolio Experiment Decks

Generated: 2026-05-14

These decks cover dashboard items `3`, `4`, and `7`.

## Open First

- `EXPERIMENT_03_ATTACK_TTP_RETRIEVAL_DECK_20260514.pptx` - selected result #2, ATT&CK TTP-set profile retrieval.
- `EXPERIMENT_04_PROVENANCE_LABEL_PATH_DECK_20260514.pptx` - provenance label path and OpTC gate.
- `EXPERIMENT_07_SEC_LORD_REDESIGN_GATE_DECK_20260514.pptx` - SEC-LoRD / DS-LoRD strict-failure redesign gate.

## Rebuild

From the repository root:

```powershell
.\.venv-diag\Scripts\python.exe scripts\build_portfolio_experiment_decks.py
```

## Scope Guard

The decks preserve the current experiment decisions:

- Experiment 3 is selected only as ATT&CK profile retrieval, not CTI prose attribution.
- Experiment 4 is a label-path decision, not a supervised provenance detector result.
- Experiment 7 is a redesign gate after a negative strict audit, not a positive extraction result.
