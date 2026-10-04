# Executive Summary

**The problem.** A model can score better while hiding more attacks. Naming the wrong attack stage can still trigger an investigation. Calling the same record benign removes that warning.

**What we tested.** We compared models on the same network records and counted correct stage names, retained warnings and false alerts. We then tested rules for keeping warnings and checked their extra review cost.

**The main finding.** In one comparison, the overall score improved while exfiltration warning recall fell from about 85% to 76%. The effect varied across runs and did not repeat in the same policy order on the second data source. In one run, 893 of 901 lost warnings had previously named the wrong attack stage. A stage-only regression count overlooks that loss; a binary warning count catches it.

**What helped, and where it stopped.** OR keeps a warning if any member warns. It cannot catch something every member misses. A later TCP/22 rule recovered the missing time-defined episode groups locally, but added 460 review cases and gave no extra exfiltration coverage on the second source. Extra explanation replay and the proposed ranking rule did not beat their simple controls.

**What the Praxis delivers.** A repeatable audit that shows which warnings disappeared, which software decision caused the loss, and what a tested repair costs. Earlier papers already establish model regression and explainable security triage. This work offers specific APT evidence and a review procedure, not a first-ever XAI claim. Human benefit and committee acceptance remain untested.
