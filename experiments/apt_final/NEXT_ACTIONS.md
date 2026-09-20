# APT final: completed comparison and optional next work

**Current status: complete and independently audited; no-go for this fixed repair family.** All nine detector variants failed the declared detection requirements on each dataset. Pooled calibration sharply reduced false alerts but also lost attack sensitivity. The strongest THEIA graph-model average improved without satisfying the required reliability checks. Read the [final report](normal_stability/results/gpu_stability_20260920/REPORT.md) and [full comparison](normal_stability/results/gpu_stability_20260920/FULL_RESULTS.md).

**Gary has no immediate action required to finish this study.** All configured cases ran, the scientific and continuation audits passed, exact replay matched earlier results, and all four AWS attempts are verified stopped. [AWS closeout](normal_stability/results/gpu_stability_20260920/AWS_CLOSEOUT.md) records approximately $1.631 in compute for this comparison, excluding storage and transfer.

**Recommendation:** rule out this tested calibration/reference repair as a demonstrated successful praxis method. Preserve the measured gains and failures together as development evidence. The broader graph-learning direction remains unresolved; no new architecture, threshold search, or checker experiment is pending under this study. The [literature assessment](embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md) and [human/source-evidence plan](normal_stability/analysis/HUMAN_REQUIREMENTS.md) document what broader claims would require.

## Optional Gary actions: reopening the original Unraveled track

These tasks apply only if the original Unraveled track is reopened; they are not prerequisites for the completed comparison.

### 1. Send this clarification request to the dataset authors

The local author README lists **Sowmya Myneni, smyneni2@asu.edu**. Current email delivery has not been verified. The [author issue tracker](https://gitlab.com/asu22/unraveled/-/issues) is another contact route. No message has been sent by the assistant.

**Subject: Unraveled dataset clarification for APT detection research**

> Hello Dr. Myneni,
>
> I am evaluating graph-based APT detection using Unraveled. Could you help clarify three points?
>
> 1. Does the release contain one continuous APT campaign or multiple independently initiated campaigns? Is there a mapping from individual records to campaign or session IDs?
> 2. Where can I find the Windows timestamp timezone and year conventions, final host-log schemas and labels, and collection-time clock verification results? The repository contains NTP synchronization code; I have not found its recorded verification results.
> 3. Are there verified links or shared identifiers connecting network flows to the corresponding host events?
>
> Links to existing documentation or annotations would be very helpful.
>
> Thank you,
> Gary Pagan

Share the reply or supporting documents in this project. A reply explaining that a mapping does not exist is useful evidence too. We can investigate another confirmation dataset while awaiting a response.

### 2. Identify one cybersecurity researcher or analyst to review a sample

Ask an adviser or colleague familiar with network records and Linux/Windows logs. Suggested request:

> Could you independently review a prepared sample for my APT research? You would see network and computer-log records side by side and mark whether each pair describes the same event, different events, or is uncertain, with a brief reason. I will provide instructions and the sample before you commit to the review workload.

The assistant will prepare the sample and instructions. The packet must include plausible matches, nonmatches, and ambiguous cases; it is not ready yet. The optional original Unraveled protocol calls for independent review, with uncertain cases escalated to another reviewer. Gary does not need to reconcile the full dataset or fill technical manifest fields manually.

## Completed assistant work

1. Froze and ran the diagnostic with separate model and reference-bank seeds, and distinct normal fit/calibration/validation graph roles.
2. Completed all nine fixed candidates on clean and 50%-masked relationships: 1,296 records per phase, 1,008 after removing identical local-feature copies.
3. Independently verified metrics, reference selections, source/data hashes, all 504 reused files, and exact agreement with the earlier completed records. All 170 documented software tests passed.
4. Preserved the previous studies, the initial bounded timeout, two bootstrap failures, and the final successful continuation. Verified shutdown for all four attempts and published sanitized operational evidence.
5. Documented concrete external-review steps without inventing an author response, completed human review, source mapping, independent campaign split, or novelty claim.

The original Unraveled E0 hold remains unchanged. Reopening it is optional and separate from this completed study.
