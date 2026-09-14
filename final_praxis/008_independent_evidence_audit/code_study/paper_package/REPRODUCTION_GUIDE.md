# Reproducing the code-study results

Start from this branch's final result commit. The original experiment source is
frozen at `162d2ab`; the prospective Qwen schema extension is frozen at `43b7d26`.
Their JSON source manifests bind exact file bytes. Later commits add audits,
compressed results, figures and writing material without changing either study.

## Reproduce the statistics without cloud spending

From the `code_study` directory, install `requirements.txt` in a Python 3.10
environment. The recorded analysis dependencies include NumPy 1.26.4. The public
package contains every assigned decision and offline row, the explicit expected
assignment inventories and unchanged result summaries. The compressed files retain
the exact original JSONL bytes and are authenticated by `PACKAGE_RECEIPT.json`.

```text
python paper_package/reproduce_statistics.py --package completed_models/original_v1 --output reproduced_original.json
python paper_package/reproduce_statistics.py --package completed_models/schema_extension_v2 --output reproduced_extension.json
```

Each command verifies source and artifact hashes, reexecutes the frozen analyses,
and compares every statistical field, including the registered 5,000-draw
bootstrap results. Only top-level provenance metadata is excluded from the value
comparison. These commands make no model requests and execute no candidate code.
Reexecuting the same implementation is distinct from the separate artifact and
statistical checks in `postrun_review/`.

Original Qwen heldout placeholders must remain in the inventory; they are
non-execution after the development gate, not measured model safety. V2 reuses
exactly the specified Devstral records and development proposals. The two versions
are not independent replications and must not be pooled to enlarge the sample.

## Reconstruct data and execution

The base is [HumanEvalPack from OctoPack](https://arxiv.org/abs/2308.07124) and the
[EvalPlus test expansion](https://arxiv.org/abs/2305.01210). Official inputs and
implementation revisions are pinned in `qualification/SOURCE_MANIFEST.json`.
`qualification/fetch_prepare.py --private-dir DIRECTORY` fetches and reconstructs
the task bundle without executing downloaded programs. The qualification protocol,
split manifest, original-test compatibility exclusions and complete qualification
receipt define the included cohort; retain all 164 source-task identities even
though only 135 qualified.

Run actual program evaluation only through the registered isolated Docker worker
and coordinator. The image, Python/NumPy versions, resource limits and comparison
predicates are recorded in `completed_qualification/`. Generated proposals have
separate admission and execution records. Do not run benchmark or generated
programs directly in the analysis environment.

Managed Bedrock model weights and sampling seeds are not hash-pinned. A fresh
provider run is a replication attempt, not a promise of byte-identical responses.
Retained requests, responses, model IDs, times, token counts and request IDs
support exact analysis of the observed run. The schema extension is a distinct
Qwen decoding configuration and may change substantive decisions.

## Raw archive custody and full audit

The complete original and extension archives are retained in the campaign S3
prefix `final-praxis/20260912/008-code-study/20260914/` in bucket
`praxis-garypagan-272615233626-us-east-1`, as `model_study_archive.tar.gz` and
`model_study_v2_archive.tar.gz`. Download receipts in `execution_receipts/` bind
their SHA-256 hashes. Access requires the owner's AWS credentials; the Git result
package supports statistical reproduction without that private archive access.

Full prompt/evidence/raw-request auditing uses these archives plus the source and
qualification artifacts. Follow `postrun_review/README.md`; its checks replay
selectors on their permitted inputs but do not execute proposals. Inspect the
scope and limitations in each audit receipt. Neither hash verification nor finite
test passing establishes universal semantic correctness, previously unseen
benchmark exposure, or publication acceptance.
