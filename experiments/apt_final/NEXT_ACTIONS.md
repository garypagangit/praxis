# APT final: what Gary needs to do next

**Current status:** The [native graph alternative](native_graph/README.md) completed its first GPU pilot on CADETS and THEIA. Independent verification passed, but recall was poor and the fixed checker gave no useful improvement. Read the [results and decision](native_graph/results/gpu_pilot_20260920/REPORT.md).

**Gary has no immediate dataset-acquisition or manual matching task for this route.** The next technical step is to compare a stronger MAGIC-style encoder and embedding anomaly score with the existing baselines before investing in a more elaborate checker. A new protocol and configuration must be frozen before that run; the completed pilot remains unchanged.

AWS sign-in was completed and the existing GPU host was used for the pilot. The job completed and the host is stopped; see [AWS closeout](native_graph/results/gpu_pilot_20260920/AWS_CLOSEOUT.json) and [connection history](cloud/README.md).

## Optional Gary actions: reopening the original Unraveled track

These tasks are not prerequisites for the active native graph experiment.

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

The assistant will prepare the sample and instructions. The packet must include plausible matches, nonmatches, and ambiguous cases; it is not ready yet. The current experiment protocol calls for independent review, with uncertain cases escalated to another reviewer. Gary does not need to reconcile the full dataset or fill technical manifest fields manually.

## Work assigned to the assistant

1. Prepare a newly frozen baseline comparison: MAGIC-style representation learning with benign embedding anomaly scoring, current reconstruction scoring, and Isolation Forest.
2. Investigate tied scores and whether detector errors are complementary, using development data with no retrospective threshold rescue.
3. Establish a useful detector before revising the checker. Evaluate any new checker against the strongest fixed detector.
4. Preserve the existing audit, negative results, and GPU receipts. GPU support, live device qualification, the first real pilot, and shutdown are completed.
5. If Unraveled is reopened, investigate its source schemas, clocks, identities, labels and campaign independence, then prepare the review packet and qualify a separate data-release validator.

The original E0 hold and CPU development registration remain unchanged. The native graph pilot has its own registration and real GPU results. No author response, completed human review, validated Unraveled join, independent campaign split, or comparative GPU speedup is claimed.
