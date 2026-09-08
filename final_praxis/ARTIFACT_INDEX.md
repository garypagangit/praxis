# Final Praxis evidence archive index

These SHA-256 hashes identify the exact downloaded or uploaded ZIP bytes. The frozen source manifests separately bind each scientific input file. Pilots and superseded versions are retained as infrastructure history and excluded from discovery results.

Raw archives are stored in the project AWS account and require authorized AWS access. Compact reports, verification summaries, and result tables are in Git. An independently verified negative result remains a completed experiment.

| Study | Archive | Bytes | SHA-256 |
|---|---|---:|---|
| 001 | superseded source v1 | 88492 | `ebf56b28e3b4f19fab5c78d94b72526e1e5009298766b3c9ce33d5a2e113be4b` |
| 001 | discovery source v2 | 164583 | `3520d37ce893406b66da830b2b060d701c7547cd9d1ea27c383ef0b618295f23` |
| 002 | discovery source v1 | 93932 | `5a7e70926543ada230b0a1d158cd24f5667f4e4ce6d738c0c01e85871583a26f` |
| 003 | superseded source v1 | 111975 | `318ed632be948e63755cfb3c8ad8499d20c1b65c3781e996aef91f5f592c0e38` |
| 003 | discovery source v2 | 227641 | `23754663859c1d115a4d46fdd0387e04244cce6328dabfc9ccd86ebb5fea248d` |
| 001 | superseded agent pilot v1 | 149520 | `3c4a2f2ea376614429b6061aa225d64afebcd1790f84c185f3f85cf4ff334a4d` |
| 001 | verified pilot v2 | 272145 | `a1ea6a9ae2759ec32f3748aca66df0adfb6f407f7e084b99d88eba5c68d4c469` |
| 002 | verified pilot v1 | 125461 | `6a804490d92b4a80042bb06108880c14f407f27ad6b18832c433096a8e6bed46` |
| 003 | superseded pilot v1 | 7637 | `506011602877b0ee342f7cb79a029698c86d0200071ede7f2e3c9153fb5fdcb1` |
| 003 | verified pilot v2 | 7862 | `21b2cf2280b2e8ed1caab1cda5597aa7ea08d4118d6d0d3307cf0e108f9584dc` |
| 002 | complete discovery v1 | 3639711 | `572bef736b087c3a6df172356e6e7557b48511be881e63c14c3f44608c9dd0ce` |

## Exact S3 locations

- 001 superseded source v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/fp001-ff19b1d1890e.zip`
- 001 discovery source v2: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/fp001-e060bb29c7e3.zip`
- 002 discovery source v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/fp002-94c2830575e9.zip`
- 003 superseded source v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/fp003-a3db8e0ed25d.zip`
- 003 discovery source v2: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/fp003-8499d656d189.zip`
- 001 superseded agent pilot v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/001/pilot_agent_v1.zip`
- 001 verified pilot v2: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/001/pilot_complete_v2.zip`
- 002 verified pilot v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/002/pilot_v1.zip`
- 003 superseded pilot v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/003/pilot_v1.zip`
- 003 verified pilot v2: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/003/pilot_v2.zip`
- 002 complete discovery v1: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/002/discovery_v1.zip`

Restore into an isolated checkout using the matching source archive and `final_praxis/shared/safe_extract.py`; do not overwrite completed runs with regenerated inputs. Run the experiment-specific independent verifier before interpreting results.
