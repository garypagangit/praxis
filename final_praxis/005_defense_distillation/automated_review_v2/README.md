# Completed automated replacement for the review queue

The current workflow processed all 28 original review cases. Its final [completion report](completion/COMPLETION.md) records 26 consensus decisions and two explicit harmfulness disagreements, which remain uncertain. Refusal labels resolve for all 28, with no differences from the original refusal labels. No further manual task is assigned. This is automated adjudication; it does not fulfill the historical requirement for independent human validation.

The frozen V2 endpoint remains 23/28. A separately labeled posthoc step verified six overlong quotations as exact passages in the source responses, shortened only their citations, and recovered three additional consensus decisions without changing any reviewer label or making model calls. The two remaining cases expose real opposing harmfulness judgments and are retained as disagreements.

See [RESULTS.md](RESULTS.md), [aggregates.json](aggregates.json), the [archive receipt](ARCHIVE_RECEIPT.json), and the [prospective V2 protocol](PREREGISTRATION.md). The [first pass](../automated_review/RESULTS.md) failed reviewer qualification and remains intact. V2 froze fresh controls and a separate rubric before its own calls. Its effective refusal rule follows substantive fulfillment of the requested task, while preserving raw labels and every override. In the completed V2 run, no actual label override was needed.

Qwen failed the reviewer controls and contributed no consensus votes. Mistral and DeepSeek qualified; their agreement is not an independent human ground truth. The selected queue contains all eight original disputes, all involving truncated responses, plus 20 agreement cases. This selection cannot yield replacement experiment-wide harm/refusal rates.

To resume the completed workflow with the same archived source bytes, run:

```powershell
python final_praxis/005_defense_distillation/automated_review_v2/workflow.py --source PATH_TO_ORIGINAL_005_OUTPUTS
```

The runner checks committed protocol bytes and source hashes, locks its output directory, and reuses verified cells without new API calls. Separate request IDs preserve intended duplicate measurements. Incomplete requests and invalid judgments receive explicit uncertainty instead of unrecorded retries. The report independently rebuilds reviewer qualification, label derivation, duplicate stability and consensus from the saved receipts. Its analysis requires no model calls.

The combined first and revised passes made 240 successful provider requests, costing an estimated $0.14245228. Serverless Bedrock performed inference; both EC2 hosts stayed stopped. Raw evidence is retained privately in checksum-verified S3 archives. Public artifacts contain labels, counts and hashes, not harmful response excerpts.
