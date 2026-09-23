# Freeze receipt line endings

The PX-080/081/082 executable sources and protocols in the pre-fit Git commits match the bytes used for their runs. The generated FREEZE.json files used Windows CRLF endings locally; Git's original automatic text normalization stored LF endings in those initial commits. Parsed JSON values and all source/data hashes are identical. This is a receipt serialization difference, not a scientific change.

The current batch-specific `.gitattributes` entry preserves exact bytes, including the original locally executed freeze receipts. No executable, model parameter, protocol, prediction, or outcome was changed to address line endings. Historical run receipts continue to identify their actual local freeze hash. The later AWS acquisition payload uses exact committed-byte verification before launch.
