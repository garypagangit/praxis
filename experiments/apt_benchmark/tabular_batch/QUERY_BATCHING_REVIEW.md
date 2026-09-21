# Query batching review for the CPU prescreen

## Conclusion

Keep the registered caveat: prevalence-adjusted metrics describe this prescreen execution. They are not measured full-E1 scores, and equal predictions under the full query roster have not been established. This was a read-only inspection of the installed TabICL 2.2.0 and TabPFN 9.0.0 source, with the explicit TabPFN 2.5 synthetic checkpoint selected by our backend. No additional fits or predictions were performed, and no frozen runner or model setting was changed.

## TabICL: an inductive inference path

The inspected path fits its feature filter, scalers, power transform, outlier handling, and ensemble shuffles on training data. Prediction reuses these fitted objects. The classifier calls the neural model without overriding `embed_with_test=False`; the column embedding and final in-context attention restrict their context to training rows. The final attention has no row-position rotary encoding in this construction. Ensemble feature/class permutations are generated during fit and reused across prediction calls.

These observations support the expectation that, in exact arithmetic, adding unrelated query rows should not deliberately change a row's prediction in this path. They do not establish bitwise equality across differently shaped numerical operations, nor were full-roster versus sampled-roster outputs compared. Our `batch_size=1` controls ensemble batching; the runner separately supplies query chunks of 1,024 rows.

Installed source locations: `tabicl/_sklearn/classifier.py:611,666`; `tabicl/_sklearn/preprocessing.py:714,1059,1070,1090,1143`; `tabicl/_model/tabicl.py:366,449`; `tabicl/_model/learning.py:94,277`. The official source also documents the default that excludes test rows from the training embedding context: [TabICL model implementation](https://github.com/soda-inria/tabicl/blob/0dbff3ec8fc68c123c87af77b0ea8b25cd2d23f3/src/tabicl/_model/tabicl.py).

## TabPFN 2.5: a potential composition dependency remains

Our `fit_mode="fit_preprocessors"` caches fitted preprocessing and transformed training data. Prediction reuses the ensemble members instead of redrawing a new ensemble. The neural attention restricts test rows to training context. However, the standard 2.5 encoder recomputes its constant-column mask and feature-group normalization mask from the concatenation of training and the current query chunk. If an internally constant training feature varies in one query chunk but not another, the encoder can keep different columns or use different group scaling. This is an unlabeled query-composition dependency, not the use of test labels. See the [official TabPFN 2.5 implementation](https://github.com/PriorLabs/TabPFN/blob/v9.0.0/src/tabpfn/architectures/tabpfn_v2_5.py).

There is an important qualification: an earlier preprocessing step removes columns constant in training, which can make the internal masks invariant for ordinary retained columns. That step occurs before later transforms, categorical encoding, SVD feature generation, and conversion to the neural model's precision. Source inspection alone therefore does not prove that every internal column varies on the selected training supports. We found a possible mechanism; we did not measure its activation or effect on this dataset.

The fingerprint feature uses row values and a training-derived salt at prediction time; repeated test rows keep their hashes. It does not intentionally redraw random identifiers for each query batch. The installed code rounds inputs before hashing to reduce numerical differences between single-row and batch transforms. TabPFN's own classifier documentation also explicitly declines a universal reproducibility guarantee from a fixed seed.

Installed source locations: `tabpfn/inference.py:682,697`; `tabpfn/architectures/tabpfn_v2_5.py:210,917,958,983,1267,1378`; `tabpfn/preprocessing/pipeline_factory.py:78`; `tabpfn/preprocessing/steps/add_fingerprint_features_step.py:26,90`; `tabpfn/classifier.py:491`.

## Reporting consequence

Report attack recall as measured on all attack rows **in this prescreen execution**, and report weighted metrics as prevalence-adjusted estimates. Keep the separate limitations from the 1,024-row normal sample and three shared-query training seeds. A future invariance check could compare the same frozen rows under different query compositions and chunk boundaries without fitting or selecting a model. That check has not been conducted here, and it would not replace full-query confirmation.

## Installed-source SHA-256 record

These hashes identify the actual inspected files; linked official repository renderings can differ in formatting.

| Package-relative file | SHA-256 |
|---|---|
| `tabicl/_sklearn/classifier.py` | `64f5ef7ef88a920a3f7a5f6e2d9d8dc08769ec343e931f910acc2d9c4eaa5534` |
| `tabicl/_sklearn/preprocessing.py` | `2163a3bf6754127365a7aedac854d99a6f565545cc1ea7e63c68a596081b2976` |
| `tabicl/_model/tabicl.py` | `583786e5ffd70b9eb425bca8e52aed415dadcdf4254c908b3b6fa52026a56491` |
| `tabicl/_model/learning.py` | `7549dff09c3796a3cb0b55ea03e249342392fa601a681526f7b1efb6a6f1eef2` |
| `tabpfn/architectures/tabpfn_v2_5.py` | `4102e5f16781107edd8effcf1ba1021f2b3660f86f3f67c687fdd8b5b95ec819` |
| `tabpfn/inference.py` | `a9eb1ca6475737cca17070768f43225479a28fe17a52f61a7aba12908b1881d7` |
| `tabpfn/preprocessing/pipeline_factory.py` | `ee6b2d7f118284c26fd742a41cc8305fe580dd81e604c53c4af0d6945bd4e679` |
| `tabpfn/preprocessing/steps/add_fingerprint_features_step.py` | `6dcf5c6723f1cd0bf418b83090e551ca6c93434e5831a8b356a9a3b35c822dce` |
