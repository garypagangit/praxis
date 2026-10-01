## 3.13 Follow-up Tests: Warning Gates, Episodes and Policy Rules

### 3.13.1 What was tested and when

PX-092 through PX-097 ask whether the warning problem can be repaired and what extra work follows. They use existing UNRAVELED and AIT data already examined by the project. Freezing their code and comparisons preserves the analysis; it does not turn these records into untouched validation. The original research questions and results remain unchanged.

PX-092 adds seven fits with new random seeds to the three original models. PX-093 adds one logistic-regression model per dataset and reuses a current-feature model. Its full ensemble has five members: three original models, a current-only model and logistic regression. PX-094 through PX-097 reuse saved predictions without retraining.

### 3.13.2 Preserving a warning

Probability averaging combines each member's class probabilities and selects the class with the largest average. The OR gate instead retains an attack warning whenever at least one member predicts any attack class. Stage refinement is separate from deciding whether to warn.

This gives a simple guarantee: a member's warning cannot disappear in the OR combination. It does not guarantee detection of attacks missed by every member, and it does not guarantee an acceptable false-alert cost. More models can add both attack warnings and benign warnings. A duplicate member cannot add coverage even if a diversity statistic changes.

Classifier combination and error diversity are established research areas (Kittler et al., 1998; Kuncheva & Whitaker, 2003). Brabec and Machlica (2018) also study aggregation for rare classes in intrusion detection. The PX-093 literature check records the overlap and distinctions. This paper claims the measured comparison and audit, not invention of OR combination or proof that it is the only possible repair.

### 3.13.3 Counting flows, episodes and investigation cases

PX-094 distinguishes three units. A flow is a recorded network exchange. An exfiltration episode proxy groups true-exfiltration flows from the same initiating host within one capture or execution; a new episode begins when consecutive start times are more than 60 minutes apart. Sensitivity checks use 30 and 120 minutes. An episode is warned only if one of its true-exfiltration flows receives a non-benign prediction.

An investigation case groups warned flows by capture/execution, source, destination and a fixed 15-minute window of flow-end time. Sensitivity checks use 5 and 60 minutes and source-only grouping. Cases are released at the window end, after their included flows have completed. Unwarned attacks that happen to share a group receive no detection credit.

The queue simulation uses one, two or four analysts and 5, 15 or 30 minutes per case. The reference is one analyst working daily 09:00-17:00 UTC at 15 minutes per case, with cases reviewed in arrival order. Handling time is assumed, not measured. Finishing a review slot does not mean an analyst recognized an attack. The protocol preserves 216 episode-result rows and 648 queue scenarios.

### 3.13.4 Checking the misses

PX-095 traces all test exfiltration rows to the original UNRAVELED CSV records. It examines episode size, the five members' predictions, training support, exact matches with benign model inputs and earlier warnings from the same source. The earlier-warning windows are 5, 30 and 60 minutes, using only flows completed before the current start. Post-hoc source details are labeled separately.

### 3.13.5 A fixed TCP/22 policy

PX-096 adds a policy warning for in-scope TCP destination-port 22 traffic without approval. Restricting network access to authorized traffic is established guidance (MITRE, 2026). The final warning is the model warning OR the policy warning. A policy approval removes only the policy restriction; it never clears a model warning. Policy violation and attack-stage prediction remain separate outputs.

The replay assumes all monitored flows are in scope and no exceptions are approved. The datasets do not contain an authoritative organizational allowlist or verified egress boundary. Therefore this is a blanket-port scenario, not proof that each match violates an actual organization's policy. It produces a deny recommendation but makes no firewall change.

The rule was chosen after inspecting the UNRAVELED misses. PX-097 applies it unchanged to Wilson and Harrison. Those executions were excluded from model training but their results had already been examined. Native destination ports are recovered from source rows and independently checked. No DNS restriction is added after observing the transfer result.
