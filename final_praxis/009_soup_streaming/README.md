# Final Praxis 009 — Soup streaming qualification

This branch qualifies an independently measured, bounded disk-read process for Soup LoRA training. [Prospective protocol](QUALIFICATION_PROTOCOL.md) fixes the research questions, correctness gates and scope before compute. Source and dataset feasibility are separate from model quality and from novelty.

Current source pin: `b0a6338232f47d7ffabac90deb810728c2e179b4` (Apache-2.0). Vendor source, temporary shards and weights belong in an external cache. No cloud job is authorized by a passing local synthetic test; the campaign coordinator controls the existing spending envelope and launch.

The core risk is already known: correct forward values can coexist with wrong adapter gradients when buffered weights are retained across backward. The comparison therefore includes matched resident numerics, nonzero adapters, all-gradient checks, short optimizer trajectories and deliberate failures. A background reader is established engineering; a novel-method claim requires a separate prior-art and efficacy gate.
