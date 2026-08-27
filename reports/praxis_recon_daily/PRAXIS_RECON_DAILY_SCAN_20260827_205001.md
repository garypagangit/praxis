# Praxis Recon Daily Literature Scan

Generated: 2026-08-27 20:50 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 1

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 12 | Cyber threat intelligence evidence routing | 2026-08-25 | Intelligent priority awareness method for alert data in SOC threat response | Journal of King Saud University - Computer and Information Sciences | [source](https://doi.org/10.1007/s44443-026-01172-w) |

## Triage Notes

### 1. Intelligent priority awareness method for alert data in SOC threat response

- Topic: Cyber threat intelligence evidence routing
- Authors: Tianqi Guo, Yan Chen, Qiang Zhang, Weiguo Wang, et al.
- Published: 2026-08-25
- Venue/type: Journal of King Saud University - Computer and Information Sciences / article
- DOI: https://doi.org/10.1007/s44443-026-01172-w
- URL: https://doi.org/10.1007/s44443-026-01172-w
- Opportunity score: 12
- Matched tags: agent, benchmark, evaluation, security, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The Security Operations Center (SOC) is a key operational platform in modern enterprise cybersecurity architectures, where alert monitoring, threat detection, and incident response must be performed under high-volume and high-noise conditions. Detection is increasingly challenged by cyberattacks with growing complexity, novelty, coordination, and stealth, resulting in massive false positives, difficulty in identifying high-risk alerts, analyst fatigue, and delayed response. This study proposes an intelligent priority awareness method for SOC alert data. First, a hierarchical alert noise reduction method is designed by combining Fast Fourier Transform-Pearson Correlation Coefficient (FFT-PCC) filtering with BERT-assisted multi-agent evidence orchestration. To prevent periodic but genuinely high-risk alerts from being mistakenly removed, the FFT-PCC module is constrained by a conservative risk-gated filtering rule that forwards any alert with threat-intelligence, asset-criticality, or attack-stage evidence to deeper analysis. On the labeled benchmark, the method achieves an AUC of 0.973, an accuracy of 0.9467, a precision of 0.923, a recall of 0.897, and an F1-score of 0.910 for false-positive alert identification. In a separate production-stream usability evaluation, it achieves a 72.0% alert noise reduction rate. Second, a dynamic risk scoring system is constructed by integrati

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

