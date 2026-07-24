# PX-061 Source Gate — Unequal Wavelet Noise and Adaptive Clipping

Date: 2026-07-24
Decision: **PASS — proceed**

## Anchor

Ranaweera et al., “Federated Learning with Differential Privacy: An Utility-Enhanced Approach”
https://arxiv.org/abs/2503.21154

## Literature-supported gap

The anchor paper applies Haar transforms, level-weighted coefficient noise, and median clipping. Its conclusion explicitly proposes:

- unequal noise across Haar coefficients; and
- dynamically adaptive clipping, particularly for non-IID federated clients.

PX-061 directly evaluates that stated future work.

## Critical validity condition

“Same nominal noise multiplier” is not enough. Every comparison must use the same adjacency definition, sampling schedule, clipping sensitivity, accountant, epsilon, and delta. An unequal-noise arm passes the mechanism gate only if its anisotropic Gaussian covariance satisfies the registered Mahalanobis-sensitivity privacy bound. Adaptive clipping must not consume unreported private information; its privacy cost must be accounted for or its statistic must be derived from already privatized releases.

## Source-gate outcome

This is a genuine extension rather than a restatement of the paper. It is experimentally feasible on public Fashion-MNIST/CIFAR-10 partitions, and positive utility is plausible because the paper already found gains from wavelet-structured perturbation while identifying these two refinements as open work.
