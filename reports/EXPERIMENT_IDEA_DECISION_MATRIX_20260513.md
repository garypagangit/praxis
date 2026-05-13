# Praxis Experiment Idea Decision Matrix

Generated: 2026-05-13

Purpose: doctoral-candidate triage of the current Praxis portfolio. This file asks whether each idea can be honestly selected, repaired, reframed, or dropped. The rule is strict: no threshold moving after outcomes are known, no relabeling weak proxies as ground truth, and no promoting an experiment unless the measured result clears the gate implied by the research question.

## Executive Decision

The current portfolio has one selected dissertation/paper lead and one promising second narrow result:

1. **Selected lead:** TTA for Streaming APT Detection / Praxis 06. The locked result is real, narrow, reproducible, and now defense-hardened.
2. **Selected next candidate:** Few-shot ATT&CK TTP-set retrieval. This is not prose CTI attribution; it is ATT&CK profile retrieval from small observed TTP sets.
3. **Reframe candidate, not selected yet:** Praxis 04 stage routing. Predicted-stage routing failed, but the rare-day oracle-stage pivot shows a real upper bound. The honest new experiment is stage prediction under day shift, not another router threshold search.
4. **Architecture track:** Provenance windowing and detector-zoo infrastructure are useful, but still label-blocked for supervised claims.
5. **Redesign gates only:** Watermarking, AI supply-chain provenance, and SEC-LoRD may still become interesting, but their current methods failed first gates.

## Definitive Matrix

| Experiment idea | What it was supposed to do | Paper/gap/future-work anchor | Status | Metrics performed vs what we needed | What happened and decision |
|---|---|---|---|---|---|
| TTA for Streaming APT Detection / Praxis 06 | Use no-label test-time adaptation plus a safety gate to recover rare APT stages under held-out source-file shift. | Wang et al. (2021) introduced fully test-time adaptation by entropy minimization; gap is adapting this idea to security streams with high-consequence classes and safety-gated overrides. | **Selected lead positive** | Needed Macro-F1 +0.05, Recon F1 +0.25, mean DE nonnegative, override <=5%, and matched reject not explaining result. Locked replay: Macro-F1 `0.8658` vs frozen `0.7685`; Recon `0.5050` vs `0.0250`; PR-AUC `0.8738` vs `0.8732`; override `0.0470`; matched reject Recon `0.0000`. Seven-seed addendum: Macro `0.8477 +/- 0.0226`, Recon `0.5147 +/- 0.0589`. | Selected. Keep original locked three-seed replay primary; use seven-seed, validation sensitivity, BN-shuffle, override decomposition, and DAPT mechanism diagnostics as defense hardening. Do not broaden to "TTA works generally." |
| DAPT2020 external TTA check | Test whether the TTA recipe transfers to another APT-flow dataset. | Same TTA literature plus the need for external validity in security ML. | **Negative appendix** | Needed positive TTA delta on DAPT. MLP recipe itself transferred: Macro `0.6353 +/- 0.0043`, Recon `0.8932 +/- 0.0089`. TTA failed: Macro delta `-0.2874`, Recon delta `-0.6589`; test DE support only `2`. | Keep as honest external-validity boundary. DAPT supports detector-recipe portability, not TTA generality. |
| Praxis 04 Stage-Conditional Routing | Extend TSE-APT style RF/MLP/BiLSTM dynamic ensembling with kill-chain stage-aware routing. | Cheng et al. (2025) propose TSE-APT and explicitly point to more realistic APT datasets plus advanced Transformer/GNN-style modeling as future work. Gap: test whether stage-conditioned routing survives temporal/source shift. | **Negative current method; reframe possible** | Needed Treatment-Stage > Baseline-TSE with p < .05, entropy concentration, rare-class gains. Five-seed: Treatment `0.5981` vs Baseline-TSE `0.6313`, p `1.0000`; router entropy near `ln(3)`. Rare-day oracle-stage pivot reached supported Macro `0.7173`, Infilteration F1 `0.5157`, but predicted-stage treatment did not. | Do not select current predicted-stage routing. Reframe only as a new stage-prediction-under-shift experiment, because oracle-stage routing proves the bottleneck is stage labels/prediction rather than the router idea alone. |
| Stage-Conditioned Class Imbalance | Rescue rare classes through stage-aware weighting/resampling. | Lin et al. (2017) motivate loss reshaping for severe class imbalance; gap is whether similar rare-class rescue works in APT flow stages. | **Dropped / parked** | Needed meaningful rare-class F1 gain without damaging benign. Best Infilteration gain only `+0.0049`; Benign F1 collapsed to `0.5481`. | Drop simple weighting/resampling. A selected result would require a new calibrated rare-class method, not parameter tweaks. |
| Stage 1 Routing Recovery | Recover Recon through a macro-policy router while avoiding Data Exfiltration harm. | TSE-APT dynamic ensemble gap and safety-constrained rare-stage routing. | **Diagnostic only** | Best macro policy `0.7723 +/- 0.0894`; Recon improved, but Data Exfiltration fell. Needed a clean improvement with DE protection. | Not selected. Useful diagnostic leading into Praxis 06's guarded decision policy. |
| Praxis 05 SAE for APT Interpretability | Use sparse autoencoders to find interpretable hidden features in APT/provenance detectors. | Cunningham et al. (2023) show SAEs can find interpretable language-model features; gap is whether detector hidden states contain decomposable security concepts. | **Hold; current MAGIC result negative** | Needed MSE ratio <=0.25, feature death <0.50, seed stability >=0.30. Full AWS Phase A: MSE ratio `0.0000224` pass, feature death `0.9119` fail, seed stability `0.2815` fail. | Do not proceed to Phase B. One PIDSMaker/larger-hidden-state pivot is allowed; relaxing gates would be post-hoc rescue. |
| SEC-LoRD / DS-LoRD | Improve model extraction or CTI task behavior by domain-seeded prompts. | Carlini et al. (2021) and related model extraction work motivate LLM leakage/extraction risks; gap is whether domain-specific CTI seeding improves extraction or task compliance. | **Current method negative; redesign gate only** | Needed seeded >= vanilla under strict parsing before extraction. Strict audit: 3B vanilla `0.276` vs seeded `0.090`; 8B vanilla `0.466` vs seeded `0.284`. Seeded prompts also caused more invalid answers. | Stop current prompt seeding. A new experiment must use retrieval-constrained evidence snippets and forced answer format, then pass strict parsing before any extraction claim. |
| AI Supply Chain Backdoor Detection | Detect poisoned/backdoored fine-tuning runs from LoRA training traces. | Gu et al. (2017) identify ML supply-chain backdoor risk; gap is provenance diagnostics over training traces rather than final model behavior alone. | **Pending weak; redesign gate only** | Needed clean/poison trace separation strong enough for detection. Real LoRA traces: loss effect `0.0401`, grad-norm `-0.0673`, update-norm `0.0203`; final validation loss poison-clean `+0.0774`. | Not selected. Build stronger poison construction and richer per-step diagnostics before multi-seed cloud replication. |
| Contrastive SSL on Provenance Graphs | Learn useful provenance graph/window representations without labels. | You et al. (2020) GraphCL shows augmentation-based graph contrastive learning can improve transfer/robustness; gap is security provenance graph representation learning. | **Pending weak / hold GPU** | Needed clear positive-negative view separation before GraphCL. Positive cosine `0.9239`, negative `0.6633`, but positive > negative rate only `0.5227`. | Do not spend GPU yet. Improve node features, augmentations, and hard negatives. |
| Continuous-Time TGN | Model provenance event streams as dynamic graphs for next-event or anomaly prediction. | Rossi et al. (2020) introduce TGN for event-based dynamic graphs; gap is applying temporal graph memory to APT provenance. | **Pending weak; reframe needed** | Needed model beat simple temporal baselines. Previous-event baseline Macro F1 `0.6044`; logistic temporal/hash features `0.5972`; no TGN detector gain established. | Reframe from next-event prediction to anomaly/window detection once labels exist. |
| APT Detector Watermarking | Embed an owner-verifiable trigger signature into APT detectors without hurting normal detection. | Adi et al. (2018) show black-box DNN watermarking by backdooring; gap is detector ownership for APT models. | **Active but failed first gate** | Needed normal Macro-F1 drop <=1 point and trigger signature >=95%. Result: Macro-F1 delta `-0.0866`; Recon fell to `0.0000`; signature stayed `0.2391`. | Do not run surrogate extraction. Redesign trigger objective or add separate owner-verification head, then rerun utility/signature gate. |
| Membership Inference Against APT Detectors | Test whether APT detectors leak training membership. | Shokri et al. (2017) define black-box membership inference with shadow models; gap is leakage in security detectors under temporal/source shift. | **Negative / parked** | RF smoke looked positive: ROC-AUC `0.6864`, AP `0.8791`. Stronger shadow protocol: same-distribution ROC-AUC `0.5599`, AP `0.5351`; temporal nonmembers `0.7256`, showing shift confound. Needed same-distribution signal >0.60. | Park. The most honest finding is that temporal shift explains most apparent leakage. |
| GNN TTP Graph Embeddings | Use graph neural embeddings for APT group attribution from ATT&CK technique profiles. | Hamilton et al. (2017) GraphSAGE motivates inductive graph embeddings; MITRE ATT&CK provides the adversary technique knowledge base. | **GNN claim dropped; simple retrieval kept** | Needed GraphSAGE beat cheap baselines. Known-profile 5-shot GraphSAGE top-5 `0.060` vs SVD `0.926` and overlap `0.985`. Held-edge GraphSAGE 5-shot top-5 `0.073`. | Do not pitch GNN. Keep ATT&CK TTP-set retrieval as the positive result. |
| Few-Shot APT Group Attribution as ATT&CK TTP-Set Retrieval | Retrieve likely ATT&CK groups from small observed TTP sets. | MITRE ATT&CK design paper motivates empirically grounded adversary technique profiles; gap is a formal few-shot retrieval protocol over group TTP sets. | **Selected next narrow result** | Baseline profile retrieval is strong: SVD top-5 `0.879` at 5 shots; overlap top-5 `0.960`; median rank `1.0`; 605 queries. Needed a repeatable protocol and honest scope. | Select as second candidate, but call it profile retrieval, not CTI prose attribution. Formal protocol now needed. |
| LLM Threat Intelligence Fusion | Fuse CTI sources with LLM/RAG to produce early-warning intelligence. | Lewis et al. (2020) RAG addresses knowledge-intensive generation and provenance; gap is CTI early-warning evaluation with dated outcomes. | **Blocked** | Existing sources support retrieval/extraction, not early-warning outcome labels. Needed dated campaign/outcome labels before model work. | Do not model first. Build an outcome-labeled evaluation set or drop. |
| Concept Drift on Provenance Detectors | Evaluate provenance detector stability over chronological host streams. | Gama et al. (2014) formalize concept drift adaptation; UNICORN shows provenance can support APT detection. Gap: drift-aware provenance detectors with real attack/benign intervals. | **Architecture-ready, label-blocked** | Full E5 Cadets: `480,537,673` events to `9,611` windows; support `9,609` attack-touch vs `2` benign/unlabeled`. Density proxy Macro-F1 up to `0.9788`, but not ground truth. Needed >=20 benign and >=20 attack/anomaly windows per label gate. | No supervised claim. Use density only for sample prioritization and representation stress tests until interval labels or OpTC subset exist. |
| Stage Routing on Provenance Graphs | Use provenance graph stage labels to route detectors by kill-chain stage. | Combines TSE-APT's stage/dynamic ensemble question with provenance APT systems such as UNICORN. | **Hold** | Needed graph stage labels and predictor better than temporal split bottleneck. Current evidence only says Praxis 04 predicted-stage routing failed. | Reopen only after graph stage labels/predictor clear a separate gate. |
| Cross-Detector Adversarial Robustness | Compare evasion robustness across 2-4 detector families. | Security ML robustness literature motivates cross-detector robustness, but this portfolio lacks stable detectors. | **Later** | Needed trained detector zoo with class support. Detector-zoo registry instantiates families, but full Cadets detector gate blocked on labels. | Do not run. Wait for 2-4 stable trained detector families. |
| Causal GNN for Evasion Resistance | Learn invariant graph rationales that resist shortcut/evasion behavior. | Wu et al. (2022) propose invariant rationales for GNN generalization under distribution shift; gap is causal/invariant provenance rationales for APT defense. | **Later** | No local gate yet. Needs detector suite and labels before causal claims are meaningful. | Keep as high-ceiling follow-on after two publishable wins. |
| Reverse TTP Extraction | Infer unknown attacker toolkit/TTPs by observing evasion queries or simulator outputs. | MITRE ATT&CK gives the target behavior vocabulary, but this requires a public simulator or query data. | **Shelved** | No public simulator/data path. Needed realistic attacker query traces or validated simulation. | Shelve until a real data source exists. |

## What Can Be Modified Without Lying

| Track | Honest modification | Why it is allowed |
|---|---|---|
| Praxis 04 | Change the research question to "Can stage labels/prediction under day shift unlock conditional routing?" | Oracle-stage pivot found a real upper bound; the failed part is predicted-stage quality. |
| Few-shot attribution | Change from "APT group attribution from CTI prose" to "ATT&CK TTP-set profile retrieval." | The data supports TTP-set retrieval but not prose-to-group attribution. |
| Provenance | Change from "supervised attack detector" to "label acquisition plus weak-proxy window prioritization." | Current labels are node-touch proxies, not interval truth. |
| Watermarking | Add owner-verification head and rerun utility/signature gate. | The current objective failed; the problem remains meaningful. |
| AI supply chain | Increase poison strength and log richer gradient/update features. | The first real trace signal is weak but not contradictory. |
| SEC-LoRD | Replace prompt stuffing with question-specific retrieved evidence and constrained answer format. | Strict parser shows current seed formatting hurts; evidence-conditioned prompting is a new method. |

## What Should Not Be Modified To Force Selection

| Track | Do not do |
|---|---|
| TTA | Do not re-search thresholds after seeing test/hardening results. |
| Praxis 04 | Do not promote predicted-stage routing by excluding the bad seed or changing the p-value gate. |
| Class imbalance | Do not hide Benign collapse to make rare-class F1 look better. |
| SAE | Do not relax feature-death from `<0.50` after observing `0.9119`. |
| SEC-LoRD | Do not use the old parser that counted letters inside non-answer text. |
| Provenance | Do not train supervised detectors on `9,609` attack-touch vs `2` benign/unlabeled windows. |
| GraphSAGE | Do not pitch GNN attribution when SVD/overlap dominate it. |

## Final Priority List

| Rank | Action | Output |
|---:|---|---|
| 1 | Finish Praxis 06 venue conversion. | Main paper package. |
| 2 | Formalize ATT&CK TTP-set retrieval. | Second narrow method/protocol. |
| 3 | Choose provenance label path, preferably targeted OpTC subset first. | Label plan and small validated window table. |
| 4 | Run only cheap redesign gates for watermarking, supply-chain provenance, and SEC-LoRD. | One-page next-gate memos plus pass/fail runs. |
| 5 | Only after labels/detectors exist, reopen drift/TGN/SSL/watermark/MIA/adversarial robustness. | Real detector suite, not proxy claims. |

## References

Adi, Y., Baum, C., Cisse, M., Pinkas, B., & Keshet, J. (2018). Turning your weakness into a strength: Watermarking deep neural networks by backdooring. In *27th USENIX Security Symposium* (pp. 1615-1631). https://www.usenix.org/conference/usenixsecurity18/presentation/adi

Carlini, N., Tramer, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, U., Oprea, A., & Raffel, C. (2021). Extracting training data from large language models. In *30th USENIX Security Symposium* (pp. 2633-2650). https://www.usenix.org/conference/usenixsecurity21/presentation/carlini-extracting

Cheng, M., Xiang, G., Yang, Q., Ma, Z., & Zhang, H. (2025). TSE-APT: An APT attack-detection method based on time-series and ensemble-learning models. *Electronics, 14*(15), 2924. https://doi.org/10.3390/electronics14152924

Cunningham, H., Ewart, A., Riggs, L., Huben, R., & Sharkey, L. (2023). Sparse autoencoders find highly interpretable features in language models. *arXiv:2309.08600*. https://arxiv.org/abs/2309.08600

Gama, J., Zliobaite, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014). A survey on concept drift adaptation. *ACM Computing Surveys, 46*(4), 1-37. https://doi.org/10.1145/2523813

Gu, T., Dolan-Gavitt, B., & Garg, S. (2017). BadNets: Identifying vulnerabilities in the machine learning model supply chain. *arXiv:1708.06733*. https://arxiv.org/abs/1708.06733

Hamilton, W. L., Ying, Z., & Leskovec, J. (2017). Inductive representation learning on large graphs. In *Advances in Neural Information Processing Systems 30*. https://papers.nips.cc/paper/6703-inductive-representation-learning-on-large-graphs

Han, X., Pasquier, T., Bates, A., Mickens, J., & Seltzer, M. (2020). UNICORN: Runtime provenance-based detector for advanced persistent threats. In *Network and Distributed System Security Symposium*. https://tfjmp.org/publication/2020-ndss/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems 33*. https://papers.nips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html

Lin, T. Y., Goyal, P., Girshick, R., He, K., & Dollar, P. (2017). Focal loss for dense object detection. In *Proceedings of the IEEE International Conference on Computer Vision* (pp. 2980-2988). https://openaccess.thecvf.com/content_iccv_2017/html/Lin_Focal_Loss_for_ICCV_2017_paper.html

Rossi, E., Chamberlain, B., Frasca, F., Eynard, D., Monti, F., & Bronstein, M. (2020). Temporal graph networks for deep learning on dynamic graphs. *arXiv:2006.10637*. https://arxiv.org/abs/2006.10637

Shokri, R., Stronati, M., Song, C., & Shmatikov, V. (2017). Membership inference attacks against machine learning models. In *2017 IEEE Symposium on Security and Privacy* (pp. 3-18). https://www.ieee-security.org/TC/SP2017/papers/313.pdf

Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and philosophy*. MITRE. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy

Wang, D., Shelhamer, E., Liu, S., Olshausen, B., & Darrell, T. (2021). Tent: Fully test-time adaptation by entropy minimization. In *International Conference on Learning Representations*. https://openreview.net/forum?id=uXl3bZLkr3c

Wu, Y. X., Wang, X., Zhang, A., He, X., & Chua, T. S. (2022). Discovering invariant rationales for graph neural networks. In *International Conference on Learning Representations*. https://arxiv.org/abs/2201.12872

You, Y., Chen, T., Sui, Y., Chen, T., Wang, Z., & Shen, Y. (2020). Graph contrastive learning with augmentations. In *Advances in Neural Information Processing Systems 33*. https://arxiv.org/abs/2010.13902
