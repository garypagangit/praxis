# APT final: what Gary needs to do next

**Update:** Gary selected the [native graph alternative](native_graph/README.md). Its immediate development pilot does not depend on an author reply or manual Unraveled event matching. The two actions below are optional work for reopening the original Unraveled track, not prerequisites for the new pilot.

AWS sign-in was completed and the expected account and existing GPU host were verified on September 19, 2026 (local time). The host is stopped. See [AWS connection and GPU plan](cloud/README.md).

## Gary: two research actions

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

1. Investigate source schemas, clock evidence, and stable identifiers; implement and verify normalization without inventing missing facts.
2. Handle duplicate observations, prepare the review packet, and populate machine-derived manifest fields.
3. Check label support and independent attack groups; qualify the data-release validator. If Unraveled contains only one APT realization, use it for development and investigate separately collected confirmation data.
4. Add and qualify GPU support in a new registered code revision, with portable checkpoints, reproducibility checks, and measured timing.
5. Run the first real comparison when its data evidence is sufficient: does using meaningful graph connections improve detection over a model that ignores them?

The original E0 hold and CPU development registration remain unchanged. No author response, completed human review, validated join, independent campaign split, or GPU speedup is claimed.
