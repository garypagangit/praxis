# PX-063 Data Attribution and Change Notice

PX-063 uses a community-normalized, TRACE-derived dataset only for evaluation.
Praxis does not redistribute the raw prompts or trajectories.

## Original work

- **Title:** TRACE (Testing Reward Anomalies in Code Environments)
- **Creators:** Darshan Deshpande, Anand Kannappan, and Rebecca Qian / Patronus AI
- **Dataset:** <https://huggingface.co/datasets/PatronusAI/trace-dataset/tree/31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d>
- **Paper:** *Benchmarking Reward Hack Detection in Code Environments via Contrastive Analysis*, <https://arxiv.org/abs/2601.20103>
- **License:** CC BY-SA 4.0, <https://creativecommons.org/licenses/by-sa/4.0/>

## Community normalization used by PX-063

- **Published as:** `ktolnos/rh-bench` by the Hugging Face account `ktolnos`
- **Dataset revision:** <https://huggingface.co/datasets/ktolnos/rh-bench/tree/1045a7336432c40182924bbd3698af292ea24acb>
- **Code/provenance revision:** <https://github.com/ktolnos/rh-bench/tree/090e47b878192ee7a016d6c89e983141a415b154>
- **Dataset-card license:** CC BY-SA 4.0
- **Code-license note:** the pinned GitHub revision contains no license file. Praxis therefore does not copy, import, or invoke its Python helpers.

## Praxis changes

Praxis filters the community dataset to `source_dataset == "patronus_trace"`,
coalesces the single populated response into a neutral in-memory trajectory,
uses pseudonymous identifiers, and applies an independently implemented
deterministic transcript-admission verifier. Committed derived artifacts contain
only cryptographic hashes, pseudonymous IDs, aggregate measurements, and
transcript-free evidence metadata. They do not contain raw TRACE text.

Any redistributable PX-063 adaptation is offered under CC BY-SA 4.0. This notice
does not alter third-party ownership, and it does not grant a license to the
unlicensed `rh-bench` repository code.
