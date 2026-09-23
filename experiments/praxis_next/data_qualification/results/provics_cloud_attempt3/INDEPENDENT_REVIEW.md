# Independent CSV review

Read-only secondary inspection on September 23, 2026; no fitting, relabeling or split changes.

The reviewer independently counted 130,940 benign physical rows, 51,425 attack physical rows and 32 ground-truth phase rows. Closed-interval intersections with physical timestamps reproduced five samples for C1 brute_force, one for C2 credential_use and zero for C4 lateral_influxdb. C2 cred_exfil also has zero samples.

These are sampling intersections, not detector results or counts of completed attacks. Material source limitations are:

- Physical timestamps use whole-second precision while annotations include milliseconds. C4 lateral_influxdb and C2 cred_exfil span only 221 ms and 10 ms, respectively.
- The cred_exfil phase is annotated Collection/T0882 and describes extracting a token from a Fuxa script. It is not a verified Exfiltration tactic event.
- The C4 movement annotation reports token=FAILED.
- C2 passive_recon describes 60 seconds of tcpdump, but the recorded interval spans only 178 ms. Action-duration semantics require review before extending labels to windows.
- The actual physical recording spans are 21 hours and approximately 52 hours, despite the directory names. Benign collection follows attack collection.
- UTC timestamp syntax does not independently establish synchronization between modalities.

The physical subset is therefore insufficient to validate the proposed movement/exfiltration evaluation. Zero exact-interval overlap does not prove that another modality lacks the event or that the attempted action did not occur. Other artifact hashes and aggregate clock calculations remain in measurement_support.json and the acquisition receipts.
