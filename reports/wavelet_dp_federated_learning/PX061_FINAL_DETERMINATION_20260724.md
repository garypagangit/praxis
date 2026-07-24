# PX-061 Final Determination

Date: 2026-07-24
Final status: **NEGATIVE — do not advance to confirmatory Fashion-MNIST**

## Question

Can unequal Haar-coefficient noise and privacy-paid adaptive clipping improve
non-IID federated-learning utility over equal wavelet noise at matched privacy?

## Evidence sequence

1. The source gate passed because the anchor paper explicitly identified
   unequal coefficient noise and adaptive clipping as future work.
2. The zCDP mechanism gate passed and verified matched privacy accounting for
   anisotropic Gaussian noise under frozen sensitivity bounds.
3. An eleven-level adaptive mechanism failed because repeated private norm
   releases destabilized clipping.
4. A registered repair reduced the release to three coefficient bands and one
   warm-up query.

## Three-band repair result

Five non-IID client partitions, total zCDP rho `1.0`, delta `1e-5`,
conservative epsilon `7.7861`:

| Arm | Mean accuracy |
|---|---:|
| Non-private clipped | 82.40% |
| Equal wavelet noise | 12.89% |
| Static unequal wavelet noise | 12.84% |
| Private adaptive unequal noise | 14.31% |

The adaptive arm beat equal noise in 4 of 5 seeds, but its mean gain was only
`1.42` percentage points. The registered gate required at least `2.0` points
and improvement in at least 4 seeds. Therefore the joint gate failed.

## Interpretation

There is weak evidence that a low-dimensional private adaptation can help, but
not enough to justify the larger confirmation. Static unequal allocation did
not improve utility. At this privacy budget and federation size, estimating
useful clipping structure consumes too much signal relative to the benefit.

## Claim boundary

This is a developmental negative result on public sklearn digits under a
conservative no-amplification accountant. It does not refute the anchor
paper's wavelet mechanism, and it does not establish behavior on Fashion-MNIST
or CIFAR-10. It does show that the proposed PX-061 extension did not clear its
precommitted feasibility gate.
