# Software qualification

32 unit/integration/refusal tests passed; all four modeling stages completed on synthetic fixtures. These are not APT detection results. Saved stage JSON files are byte-identical receipts from the synthetic run; runtime model weights and per-row synthetic predictions are not shipped. Regenerate them with the smoke command. The first fixture permitted under 50% rewiring because it included forced lag-1 chains; the final fixture uses lags 2/5/8 and exercises 79.7%/79.2% changed edges. No real-data policy or endpoint was tuned through this fixture change.
