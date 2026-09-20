# CTI behavior-mapping fallback: data readiness

Date: 2026-09-20. **Readiness inspection only: no model fit, efficacy score, or positive result.** Related literature and novelty assessment: [CTI pivot research](PIVOT_CTI_RESEARCH_20260920.md).

## Decision

The existing AnnoCTR **training and development** files support an inexpensive actor-name dependence screen. CPU text classification is sufficient for that initial diagnostic. It would establish whether a particular lexical baseline has a useful failure to address; it would not establish a neural-model limitation, deployment readiness, or a novel praxis.

The meaningful intervention is to remove incidental actor/group identities while preserving described actions. The task is **mapping report evidence to ATT&CK techniques**, not attributing an intrusion to its perpetrator.

No final test file was downloaded or read during this readiness inspection. The final test remains outside the following proposed development screen.

## Acquired files and license

Source: [author repository](https://github.com/boschresearch/anno-ctr-lrec-coling-2024/tree/d510b6949e1938d47c93a43eedd562dc538439dc), pinned commit `d510b6949e1938d47c93a43eedd562dc538439dc`. The corpus is **CC-BY-SA 4.0** according to its README/license. Local acquisition: `C:/w/apt_pivot_20260920/annoctr_readiness/`; `ACQUISITION.json` records bytes and hashes. All files below were actually downloaded and read.

| Exact relative file | Bytes | SHA-256 |
|---|---:|---|
| `LICENSE.txt` | 20,137 | `23ee78c8bae49cf08ea2f0c84945c66b987ebe4520881fb51b3dad4fb43d07c2` |
| `README.md` | 3,732 | `a4083bfb8d5435e019f742e7477a39fa54d01e3c1d1724f29b6763c6314efc22` |
| `AnnoCTR/ner_json/train.json` | 8,193,379 | `4e98d5949a77ce0a4c67eb6babb7502f9e84936dc3bc677356869c88097393f3` |
| `AnnoCTR/ner_json/dev.json` | 2,945,542 | `e6af35b9666c0c2a5bcb5779d296247d94b724e4d31b2e11cf4e18a796639137` |
| `AnnoCTR/linking/train_w_con.jsonl` | 13,199,220 | `988a9e1d2708fa91f944087b70e1f2f2c50c4398db09e9d3542978403ab1365b` |
| `AnnoCTR/linking/dev_w_con.jsonl` | 4,611,104 | `babca37f8523b3f1748810b1641a95bd7cc8270e2193133e09a460959785e18f` |

The repository tree was inspected to identify split paths; listing a test filename is not reading its contents. Raw per-report paths are `AnnoCTR/text/train/<document>.txt` and `AnnoCTR/text/dev/<document>.txt`; their bytes were not required or acquired because the downloaded NER files contain the complete sentence text and document identifiers.

## Schema and leakage controls

The NER `.json` files are **JSONL**, one sentence per record. Fields include `id` (`<document>__sNNNN`), `text`, `tokens`, and aligned BIO tag lists. `ce_tags` contains explicit cybersecurity entities; `ci_tags` contains implicit concepts. All 320 training and 89 development sentences with explicit GROUP tags permitted exact left-to-right token alignment to their original sentence text. This yields 401 training and 99 development actor/group spans without changing the action words.

The linking files contain `mention`, `_context_left`, `_context_right`, adjacent sentence text, document ID, and gold target fields. Reconstructing `_context_left + mention + _context_right` identifies the current annotated sentence. Match it to NER text within the same document after whitespace normalization; do not use a gold mention alone as model input.

**Model input must be complete ordinary sentence text**, optionally the preceding/current/following sentence window. Gold `label`, `label_title`, `label_id`, `label_link`, entity tags, and label-bearing document filenames are target/annotation data only. In particular, `label` contains the target's descriptive text and would leak the answer if included.

Target validation is necessary: `entity_type == TECHNIQUE` is insufficient. There are 32 training and six development records with that type but a software or internal Bosch placeholder URL. Require a genuine ATT&CK technique URL of the form `/techniques/Tdddd[/ddd]`, preserving subtechniques.

The conservative readiness join excluded ambiguous repeated sentences, invalid target mappings, and remaining technique-tagged sentences lacking a valid joined target. It did not silently turn those unresolved examples into negative labels. There are also 14 training and three development valid-target linking records whose reconstructed sentence did not match exactly. A registered pilot must save its complete exclusion ledger and qualify this join independently.

## Measured data support — not model results

| Quantity | Training | Development |
|---|---:|---:|
| Documents / NER sentences | 70 / 7,570 | 16 / 1,550 |
| Documents containing explicit actor/group names | 35 | 11 |
| Valid technique linking records before sentence join | 1,915 | 445 |
| Distinct valid technique targets before join | 125 | 53 |
| Sentences retained by conservative join | 7,514 | 1,540 |
| Sentences excluded by that policy | 56 | 10 |
| Retained sentences with technique targets | 1,479 | 330 |
| Same-sentence actor name and technique target | 58 | 20 |
| Technique-positive sentence with actor name in its three-sentence window | 110 | 58 |
| Documents supporting those windows | 27 | 10 |
| Technique labels supported by at least two documents after join | 82 | 24 |

After joining, training supplies 124 labels; six of the 53 development labels are unseen in training. Preserve and report those unsupported labels rather than dropping their missed predictions to improve the score. The corpus includes criminal groups and general CTI as well as APT reports; the resulting claim must retain that scope.

A naive alias detector built from training GROUP linking rows is **not ready for use**: some implicit GROUP rows contain whole behavioral phrases, and short names such as `TEMP` or `Cobalt` can match unrelated content. Restricting to genuine explicit actor spans helps, but a deployable detector still requires separate qualification. The train/dev gold spans can support an explicitly labeled **oracle diagnostic**; that intervention is not the proposed production system.

## Lowest-cost meaningful screen

1. Freeze the training/development files, conservative join, exclusions, complete label space, and document grouping before modeling. Preserve all eligible unlabeled sentences as benchmark negatives; do not interpret these annotations as proof that a sentence contains no malicious activity.
2. Fit one CPU baseline: word unigram/bigram TF-IDF with one-vs-rest logistic regression, fixed hyperparameters and seed. Use current plus neighboring sentence text as input but only the current sentence's technique targets. Training-only fitting includes vocabulary and IDF statistics. No test access, threshold search, encoder training, or new checker family is needed.
3. On development data, compare that **same frozen model** on original windows versus windows in which only verified gold actor/group spans become a neutral `ACTOR` token. Include all development examples and separately identify the 58 positive actor-bearing windows across ten documents. This is an oracle ablation diagnostic, not a deployable-model comparison.
4. Report exact multi-label precision/recall/F1 on real unmodified development text, then count beneficial and harmful prediction changes after masking. Report changes by document, including unsupported labels, rather than treating overlapping windows as independent evidence. A change in output alone is not an improvement.
5. Only if enough real baseline errors improve without materially damaging correct behavior predictions should a second experiment compare ordinary training, mask augmentation, and consistency training using a qualified non-oracle actor detector. A future improvement requires untouched report evaluation; current development results cannot become the final evidence.

The available support is adequate for a cheap diagnostic, not a narrow confidence interval: ten development documents support the relevant positive windows, and windows overlap. A CPU baseline is sufficient to decide whether **its** actor-name sensitivity merits work. If it shows no headroom, an encoder would be a separate, justified hypothesis—not something automatically required to keep searching for a positive result.

## Present status

Data is locally accessible and schema problems are identified. No human annotation is required for the proposed gold-span diagnostic. A production claim would need independently validated actor-span detection; a novel contribution would still need to surpass existing masking, augmentation, and counterfactual-evidence methods identified in the linked literature review.

**No training, efficacy scoring, AWS use, or positive-result claim occurred in this readiness task.**
