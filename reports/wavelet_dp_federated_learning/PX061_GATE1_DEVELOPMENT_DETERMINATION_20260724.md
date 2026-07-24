# PX-061 Gate 1 Development Determination

Date: 2026-07-24
Status: **SUPERSEDED — Haar level grouping defect found during Gate 1B diagnostics**

> This determination is retained for audit history but is not scientific evidence.
> The packed Haar layout was grouped incorrectly as `1,2,4,...` rather than
> `1,1,2,4,...`. Corrected runs supersede all metrics below.

## Result

The three-seed public-data development harness completed with conservative composed privacy of:

- epsilon: `7.7861`
- delta: `1e-5`
- total zCDP rho: `1.0`

Mean test accuracy:

| Arm | Accuracy |
|---|---:|
| Non-private | 79.33% |
| Equal wavelet Gaussian | 18.59% |
| Privacy-optimized unequal wavelet Gaussian | 18.59% |

The equal and unequal arms were identical for every seed.

## Why this happened

The frozen level clipping bounds were proportional to the square root of the number of coefficients in each Haar level. Under the matched zCDP constraint, this makes the minimum-total-variance anisotropic solution collapse algebraically to equal per-coordinate variance.

This is a useful negative design result:

- unequal coefficient noise cannot be justified merely by observing that some coefficients look more important;
- a valid gain requires separately established per-level sensitivity bounds;
- if those bounds are learned from private client updates, their release must consume privacy budget;
- adaptive clipping must therefore be privatized and included in the same accountant.

## Next gate

Implement a two-budget mechanism:

1. reserve a registered fraction of rho for privatized per-level norm/quantile estimation;
2. set the next-round clipping envelope only from that private release;
3. allocate the remaining rho optimally across the resulting sensitivity bounds;
4. compare with equal-noise and anchor-weighted baselines at matched realized epsilon.

No positive utility claim is supported by this development run.
