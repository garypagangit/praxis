# Audit run history

1. Initial local audit execution completed fixture evaluation but failed while encoding the diagnostic JSON with `allow_nan=False`: upstream reference answers contain nonfinite NaN values. Exit code 1; no completed audit was claimed.
2. The audit reporter was corrected to tag nonfinite values in output receipts only. Source bytes and values supplied to the upstream scorers were unchanged. The completed rerun is in `AUDIT.json` and `audit_stdout.txt`.
