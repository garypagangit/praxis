# Praxis Recon Daily Literature Scan

Generated: 2026-08-09 11:18 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Adaptive evaluation of deterministic agent defenses | 2026-08-07 | Adversarial Machine Learning for Secure and Explainable AI Systems: A Comprehensive Review | Journal of Cybersecurity and Privacy | [source](https://doi.org/10.3390/jcp6040132) |
| 2 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-08-07 | L-ARLPT: An LLM-Augmented Reinforcement Learning Framework for Autonomous Penetration Testing | Applied Sciences | [source](https://doi.org/10.3390/app16167887) |

## Triage Notes

### 1. Adversarial Machine Learning for Secure and Explainable AI Systems: A Comprehensive Review

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Hajar Ouazza, Fadoua Khennou, Abderrahim Abdellaoui
- Published: 2026-08-07
- Venue/type: Journal of Cybersecurity and Privacy / article
- DOI: https://doi.org/10.3390/jcp6040132
- URL: https://doi.org/10.3390/jcp6040132
- Opportunity score: 10
- Matched tags: agent, evaluation, open problem, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Adversarial machine learning (AML), reinforcement learning (RL), and explainable artificial intelligence (XAI) are increasingly studied as separate problems, yet their interactions under realistic threat conditions remain poorly understood. This review addresses that gap through a systematic analysis of 207 studies selected from 4447 records following the PRISMA 2020 guidelines, covering work published between 2020 and 2026 across cybersecurity and computer vision. A taxonomy of adversarial attacks is constructed across training and inference phases, defense mechanisms are examined with attention to their documented failure modes, and robustness evaluation practices are assessed across the surveyed literature. RL is analyzed in both offensive and defensive roles. Attack agents using RL achieve evasion rates of 74–97% against ML-based detectors, while RL-based defenses report robustness gains of up to 3× over static baselines under comparable threat conditions. XAI receives particular attention because the field treats it almost exclusively as a transparency mechanism, whereas the reviewed evidence shows that it also functions as an attack surface. Attribution methods such as LIME, SHAP, and Grad-CAM produce unreliable explanations under adversarial perturbation, and no system in the reviewed literature certifies that attribution properties are maintained when inputs are manipul

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. L-ARLPT: An LLM-Augmented Reinforcement Learning Framework for Autonomous Penetration Testing

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Rufeng Zhan, Junyi Zhu, Yinghui Xu, Chan Chen, et al.
- Published: 2026-08-07
- Venue/type: Applied Sciences / article
- DOI: https://doi.org/10.3390/app16167887
- URL: https://doi.org/10.3390/app16167887
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> In recent years, Deep Reinforcement Learning (DRL) has emerged as a promising approach for automating penetration testing due to its capability to perform sequential decision-making in complex environments. However, in real-world enterprise networks, attack actions are typically characterized by highly coupled multi-dimensional parameter combinations, resulting in an exponentially expanding discrete action space. Such a large action space significantly degrades exploration efficiency and prevents conventional DRL agents from learning effective attack paths under sparse-reward conditions. To address these challenges, this paper proposes a Large Language Model-enhanced Autonomous Reinforcement Learning Penetration Testing framework (L-ARLPT). Specifically, the framework leverages the domain knowledge embedded in a Large Language Model (LLM) to perform tactical planning, thereby pruning the original action space into a compact set of candidate actions. Subsequently, an experience-driven layer employs the optimization mechanism of a Deep Q-Network (DQN) to conduct value estimation and policy learning within the reduced candidate set. To validate the effectiveness of the proposed framework, a high-fidelity enterprise penetration-testing simulation environment was constructed based on realistic enterprise attack scenarios. Experimental results demonstrate that, in a high-fidelity ent

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

