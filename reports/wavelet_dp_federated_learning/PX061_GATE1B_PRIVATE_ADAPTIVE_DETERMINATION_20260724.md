# PX-061 Gate 1B — Privatized Adaptive Sensitivity Determination

Date: 2026-07-24
Status: **NEGATIVE DEVELOPMENTAL RESULT**

This determination uses the corrected packed Haar grouping:

`1 approximation, then 1, 2, 4, ..., n/2 detail coefficients`.

All private arms used the same total privacy budget:

- total zCDP rho: `1.0`
- conservative epsilon: `7.7861`
- delta: `1e-5`
- no subsampling amplification claimed

Mean accuracy across three non-IID client partitions:

| Arm | Accuracy |
|---|---:|
| Non-private clipped | 81.26% |
| Equal wavelet noise | 17.63% |
| Static unequal wavelet noise | 17.70% |
| Privatized adaptive unequal noise | 7.48% |

The static unequal allocation improved the equal arm by only `0.07` percentage
points, far below the preregistered two-point target. The private adaptive arm
was materially worse because the per-level norm releases were too noisy and
caused unstable clipping envelopes.

## Determination

The proposed adaptive mechanism is not ready for Fashion-MNIST confirmation.
Under strict matched accounting, a small non-IID federation cannot cheaply
estimate eleven level bounds every five rounds. Proceeding directly to a larger
dataset would spend compute without a plausible mechanism.

The next defensible repair is to reduce the private query dimension and
frequency—for example, three precommitted coefficient bands and one warm-up
release—while keeping the same total privacy budget. That repair requires a new
development registration and cannot be presented as confirmation of the
current adaptive design.
