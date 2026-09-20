# E0 execution notes

The first invocation stopped during schema inspection, before any output result was written: a source CSV record had fewer fields than its declared header, so Python's CSV parser returned `None` for Stage and a string operation failed. The parser was corrected to preserve that record as `undeclared_or_empty_label` and count the schema failure. No source data, label, timestamp, or threshold was changed. A regression test covers the case. The next invocation completed and produced the frozen receipts in this folder.

Additional interpretation of the completed outputs:

- All 435,488 cached Signature fields are empty. The current cache cannot reconstruct attacker or campaign assignments; the raw sources and author mappings must be revisited.
- The 22,144 valid-time flow records and 1,401 valid-time host records came from beginnings of files. The zero interval coincidences establish only that this particular bounded sample did not supply candidate pairs. They do **not** establish a 0% join success rate or prove that the full dataset cannot be joined.
- Host schema/label failure counts include limitations of the explicitly documented bounded parser. They must not be generalized into claims that the full source release is invalid. In particular, right-tail physical-line parsing does not implement recovery of multiline host records, and undeclared Windows fields cannot safely be assumed to be labels.
- Raw source prefix bytes read: 436,052,087. Only aggregate statistics and hashes are retained. The source files total substantially more bytes; full raw-dataset content hashes are not claimed.
- Audit UTC time crosses into September 20; the experiment folder is labeled for September 19 in the user's America/New_York timezone.
