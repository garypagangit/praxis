# SEC-LoRD Relationship-Evidence Gate

Generated: 2026-05-16

Status: **stronger retrieval gate ready; still no extraction claim**

## Bottom Line

The previous retrieved-evidence gate was too shallow because it only attached short technique facts. This gate retrieves from an ATT&CK snapshot closer to the CTI-MCQ source era and ranks relationship-level evidence: mitigations, detection/data components, procedure examples, tactics, and technique metadata.

This is the best honest way to give SEC-LoRD a chance: improve evidence selection, keep vanilla and broad-seed controls, and require the same strict pass gate before any extraction work.

## Generated Artifacts

- Prompt JSONL: `runs\sec-lord-relationship-evidence-gate-20260516\relationship_evidence_prompts.jsonl`
- Evidence-addressable prompt JSONL: `runs\sec-lord-relationship-evidence-gate-20260516\evidence_addressable_prompts.jsonl`
- Summary JSON: `runs\sec-lord-relationship-evidence-gate-20260516\summary.json`

Regenerate command:

```powershell
.\.venv-diag\Scripts\python.exe .\scripts\build_sec_lord_relationship_evidence_gate.py
```

## Input And Retrieval Summary

| Item | Value |
|---|---:|
| CTI-MCQ rows | `500` |
| ATT&CK bundle | `enterprise-attack-12.0` |
| Rows with evidence | `486` |
| Evidence coverage | `0.972` |
| Expected option phrase appears in retrieved evidence | `0.478` |
| Expected option is unique top lexical support | `0.356` |
| Primary evidence-addressable rows | `106` |
| Primary evidence-pointer audit accuracy | `0.811` |
| Diagnostic evidence-addressable rows | `130` |
| Diagnostic evidence-pointer audit accuracy | `0.846` |

## Prompt Conditions

| Condition | Purpose |
|---|---|
| `vanilla_strict_prompt` | Strong plain baseline with exact `Answer: <A|B|C|D>` output requirement. |
| `broad_seed_negative_control_prompt` | Keeps the failed domain-stuffing strategy visible as a negative control. |
| `relationship_evidence_prompt` | Uses question-ranked ATT&CK relationship evidence instead of broad seed stuffing. |

## Pass Gate

- Relationship-evidence strict accuracy must beat vanilla by at least `+0.030` absolute.
- Relationship-evidence invalid response rate must be no worse than vanilla.
- Evidence-only paired wins must exceed vanilla-only paired wins.
- Broad seed negative control remains reported and cannot be hidden.

## Audit Note

The lexical support audit uses labels only after retrieval to estimate whether the retrieved evidence contains answer-bearing text. It is not a model result and it is not a pass claim.

## Previous Llama Baselines On Primary Addressable Slice

| Model | Vanilla strict acc | Broad-seed strict acc | Vanilla invalid | Broad-seed invalid |
|---|---:|---:|---:|---:|
| Llama-3.2-3B-Instruct | `0.311` | `0.085` | `50` | `95` |
| Llama-3.1-8B-Instruct | `0.538` | `0.245` | `16` | `57` |

## Sample Retrieved Evidence

### cti_mcq_8 / T1548.001

- Expected: `B` / `M1028 - Operating System Configuration`
- Evidence pointer: `B`
- Support scores: `{'A': 0.25, 'B': 14.0, 'C': 0.0, 'D': 0.25}`
- `mitigation`: Mitigation M1028 Operating System Configuration for T1548.001 Setuid and Setgid: Applications with known vulnerabilities or known shell escapes should not have the setuid or setgid bits set to reduce potential damage if an application is compromised.
- `parent_detection`: Detection for T1548 Abuse Elevation Control Mechanism: Monitor the file system for files that have the setuid or setgid bits set.
- `technique`: Technique T1548.001 Setuid and Setgid: An adversary may abuse configurations where an application has the setuid or setgid bits set in order to get code running in a different (and possibly more privileged) user's context.

### cti_mcq_10 / T1134.003

- Expected: `D` / `Privileged Account Management`
- Evidence pointer: `D`
- Support scores: `{'A': 0.25, 'B': 0.25, 'C': 0.0, 'D': 14.0}`
- `mitigation`: Mitigation M1026 Privileged Account Management for T1134.003 Make and Impersonate Token: Limit permissions so that users and user groups cannot create tokens.
- `mitigation`: Mitigation M1018 User Account Management for T1134.003 Make and Impersonate Token: An adversary must already have administrator level access on the local system to make full use of this technique; be sure to restrict users and accounts to the least privileges they require.
- `parent_procedure`: Procedure example for T1134 Access Token Manipulation: S0697 HermeticWiper - HermeticWiper can use `AdjustTokenPrivileges` to grant itself privileges for debugging with `SeDebugPrivilege`, creating backups with `SeBackupPrivilege`, loading drivers with `SeLoadDriverPrivilege`, and shutting down a local system with `SeShutdownPrivilege`.

### cti_mcq_11 / T1134.003

- Expected: `B` / `Cobalt Strike`
- Evidence pointer: `B`
- Support scores: `{'A': 0.0, 'B': 14.0, 'C': 0.0, 'D': 0.0}`
- `procedure`: Procedure example for T1134.003 Make and Impersonate Token: S0154 Cobalt Strike - Cobalt Strike can make tokens from known credentials.
- `parent_procedure`: Procedure example for T1134 Access Token Manipulation: S0697 HermeticWiper - HermeticWiper can use `AdjustTokenPrivileges` to grant itself privileges for debugging with `SeDebugPrivilege`, creating backups with `SeBackupPrivilege`, loading drivers with `SeLoadDriverPrivilege`, and shutting down a local system with `SeShutdownPrivilege`.
- `mitigation`: Mitigation M1026 Privileged Account Management for T1134.003 Make and Impersonate Token: Limit permissions so that users and user groups cannot create tokens.

### cti_mcq_19 / T1110.001

- Expected: `D` / `MSSQL`
- Evidence pointer: `D`
- Support scores: `{'A': 0.0, 'B': 0.5, 'C': 0.0, 'D': 14.0}`
- `procedure`: Procedure example for T1110.001 Password Guessing: S0532 Lucifer - Lucifer has attempted to brute force TCP ports 135 (RPC) and 1433 (MSSQL) with the default username or list of usernames and passwords.
- `procedure`: Procedure example for T1110.001 Password Guessing: G0007 APT28 - APT28 has used a brute-force/password-spray tooling that operated in two modes: in brute-force mode it typically sent over 300 authentication attempts per hour per targeted account over the course of several hours or days.
- `procedure`: Procedure example for T1110.001 Password Guessing: S0020 China Chopper - China Chopper's server component can perform brute force password guessing against authentication portals.

### cti_mcq_23 / T1110

- Expected: `C` / `T1110`
- Evidence pointer: `C`
- Support scores: `{'A': 0.0, 'B': 0.0, 'C': 14.0, 'D': 0.0}`
- `technique`: Technique T1110 Brute Force: Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.
- `data_source`: Data sources for T1110 Brute Force: Command: Command Execution, Application Log: Application Log Content, User Account: User Account Authentication.
- `detection`: Detection for T1110 Brute Force: Monitor authentication logs for system and application login failures of Valid Accounts.

## Decision

SEC-LoRD remains negative for the old broad-seeding method. This relationship-evidence gate is the recommended next model run. No extraction experiment should run until it passes.
