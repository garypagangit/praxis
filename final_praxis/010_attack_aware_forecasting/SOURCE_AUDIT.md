# Source and data audit

Audit performed before pretrained-model inference, September 14, 2026. Exact revisions and bytes are in SOURCE_MANIFEST.json and RUNTIME_ASSET_MANIFEST.json. Original sources remain unchanged outside Git and are reconstructed by code/prepare_assets.py. Notebook installation directives and plotting are never executed.

## June attack detector

Primary paper: Sribalaji C. Anand, Anh Tung Nguyen, and George J. Pappas, [Attack Detection using Time Series Foundation Models](https://arxiv.org/abs/2606.06347v1), June 2026 preprint. Original [code revision](https://github.com/balajianand1994/Attack_detection_using_TFM/tree/4c1b83d14a9bc4fed22828d33dd4a3be4a2f93e2) has six scripts and no explicit repository license. Scripts are fetched to the external cache; they are not redistributed in this branch.

`1_replay_lti_final.py` lines 13–18 load TimesFM 2.5; lines 24–128 define the system and calibration; lines 146–229 run 20 trials. Lines 202–206 blend predicted/observed values after a chi-square alarm only when `t >= attack_start`. This differs from the paper's alarm-freeze description. Our historical execution preserves that oracle onset gate and the 0.8 blending weight, with additive recording instrumentation. Three separately named deployable controls use rolling context, alarm-only blending, and literal context freezing. They never receive an attack label or attack onset. Clean and attacked streams receive each policy symmetrically in those controls.

The original script does not pin its TimesFM Git revision or model revision and provides no numerical golden receipt. Our exact source reproduction therefore means running the pinned released numerical script with pinned current compatible 2.5 artifacts; it cannot establish bitwise identity with the authors' unrecorded environment. CPU equality is independently testable because the published observer requires no FM. It passed with zero difference on all 20 trajectories/residuals and matched decisions.

## ICLR calibration base

Natalia Martinez Gil, Fearghal O'Donncha, Wesley M. Gifford, Nianjun Zhou, Dhaval C. Patel, and Roman Vaculin, [Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring](https://arxiv.org/abs/2604.20122v1), ICLR 2026. The [official notebook package](https://github.com/ibm-granite/granite-tsfm/tree/fe7a35697723e2a2f5246ae979474bfc554e26c0/notebooks/hfdemo/adaptive_conformal_tsad) names NAB and Chronos Bolt Small among its evaluated data/models. It delegates scoring to `tsfm_public/toolkit/w1acas.py` and `conformal.py`.

Our wrapper uses the original context-construction function and original W1ACAS code; Chronos inference matches the original expanding-window, BF16, batch-128, median-forecast path. Toolkit package stubs load only its five reviewed modules, bypassing unrelated model imports; no numerical method is replaced. Serialization/network helper definitions are present in the upstream modules but never called. No Hugging Face remote custom code is enabled.

`main_acas_w1.py` lines 232–240 chooses a label-informed PA-F1 threshold and then compares p-values to that threshold. We intentionally do not execute that evaluation path. The precompute protocol instead fixes alpha 0.01, retains raw pointwise outcomes, and avoids a point-adjusted success claim. This is a forecasts-and-score reproduction with a declared evaluation change, not an exact recreation of published summary metrics. The paper's full aggregate benchmark is outside Q1.

The shipped NAB example is [TSB-AD 001_NAB](https://github.com/TheDatumOrg/TSB-AD/blob/6beac72e11d1155ade40870492c00d0d1cfdcaaf/Datasets/TSB-AD-U/001_NAB_id_1_Facility_tr_1007_1st_2014.csv). All 4,031 rows are development reproduction data. Original train boundary 1007 leaves 3,024 scored positions. The bulk TSB-AD ZIP returned HTTP403; the exact public example was accessible. This is no substitute claim about SWaT/HAI attacks. Dataset access and licensing trace to the original source; the curation code license does not replace underlying dataset rights.

Synthetic checks verify every context's last index precedes its first target, trailing missing targets remain explicit, horizons align to the same observation, and future score changes leave past W1ACAS outputs unchanged. They do not prove every possible temporal or statistical guarantee.

## TimesFM 3

Official source revision [8cb0628](https://github.com/google-research/timesfm/tree/8cb0628371af142e16b8c232cc9fbf667ffb12f9); [weights revision43046b8](https://huggingface.co/google/timesfm-3.0-pytorch/tree/43046b85ec22d584a13f8098c2ed39c889e129c2). Source is Apache2.0; version3 weights have a separate noncommercial/nonproduction license. Exact license bytes are pinned. The safetensors payload is 1,322,898,824 bytes. Actual peak memory and latency are measured during Q1; this file size is not a whole-process memory estimate.

The evaluator uses native variate attention, no future covariates, no input normalization override, and no symmetric averaging. `make_positive=False` is explicit because the fixed synthetic control has signed measurements. It measures three-channel forecasts; replacing the FM with last-value predictions would not satisfy this gate.

## HAI access and chronological isolation

HAI source revision [2a814ce](https://github.com/icsdataset/hai/tree/2a814cebc9a66b06c9e5cd545e2d72e65d383737). README License section states CC BY-SA4.0; an embedded metadata block elsewhere says CC BY4.0. Preserve the explicit license statement and disclose the inconsistency rather than infer a more permissive license. No raw HAI data is redistributed in Git.

The exact HAI21.03 train1 gzip matched its Git blob and contained 216,001 chronological one-second observations, 84 columns including time/labels. It is real CSV, not an LFS pointer. No train2/train3/test file was opened for outcomes, and no HAI model efficacy was computed. All eight upstream compressed-file identities are inventoried for later splits. HAI is an industrial testbed dataset, not production incident sampling; HAIEnd is not independent replication of shared episodes.

## Interpretation boundary

The simple controls show how a predictable persistent signal can lose detection. Identical observed streams assigned malicious versus benign semantic labels necessarily produce identical outputs from the same detector. A future defense therefore needs an explicit observable provenance assumption or a measurable retention/recovery tradeoff. The CPU pilot alone does not establish the proposed cross-channel modification, FM superiority, cybersecurity efficacy, or publication-level novelty.
