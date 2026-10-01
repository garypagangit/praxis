# Executive Summary

**The problem.** A security model can score better while letting more attacks pass without a warning. Calling an attack the wrong type can still prompt an investigation. Calling it benign can hide it. A single overall score does not show that difference.

**What the main experiment found.** In one comparison, the overall score improved, but the share of exfiltration records receiving any attack warning fell from about 85% to 76%. The size of the change varied across training runs. The same policy ordering did not repeat on the AIT test source.

**What helped.** A simple OR rule keeps a warning whenever any member model flags an attack. It stops the combination step from erasing an available warning. It cannot help when every member calls the event benign.

**What the repair tests found.** Adding a TCP/22 policy rule raised UNRAVELED episode coverage from 6 of 18 to 18 of 18. It also added 510 benign-labeled flow warnings and 460 grouped investigation cases. The twelve recovered episodes were small, time-defined groups from one endpoint pair, not twelve confirmed theft incidents. On AIT, exfiltration used UDP/53, so the unchanged TCP/22 rule added no exfiltration coverage.

**What to do with this result.** Review model updates using attack warnings, stage accuracy and benign workload together. Keep mandatory policy decisions explicit so a model cannot override them. Test the policy on traffic it covers and on other attack channels. The study supports this review method and a limited local repair; it does not establish a universal exfiltration detector or prove that theft was prevented.
