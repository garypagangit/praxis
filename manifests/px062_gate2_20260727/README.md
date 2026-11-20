# PX-062 Gate 2.1 Registered Retry

Registered before SageMaker job creation: **2026-07-27 03:58:10 UTC**.

The one authorized job is `px062-g21-retry1-20260727`. It must be created from
the byte-exact request in `retry_request.json` only after the account's single
`ml.g5.2xlarge` training slot is free. The registered launcher independently
checks the request hash and the immutable S3 object version before submission.

## Frozen evidence

- Source commit: `7ecef81fe50f68eb0546279a1b6d70f2ecfb85d8`
- Request SHA-256:
  `4969e6915acae09e178744ac91e46533ee8e42cfbd8f89bfe28d1786522955bf`
- Source archive SHA-256:
  `d74e5ff5235806b777e7cda8fd0b71968c3526c60608347bdbfd9a9b9ac0ab22`
- S3 version ID: `MVESPnZrotIUzZn3k483ZoweJj9057j2`
- S3 ETag: `92c4e8fc56fb448010a239982f6c0b5f`
- IAM policy SHA-256:
  `3cf8ccda6bb5986c5bbc2edfc45ff375e7a7f4379869ee37a410967061f63511`
- Frozen task SHA-256:
  `fbda2e8039d2a6087fb1cd3584470269c3e2c409d4bbe13f7eb1e59a4fc19316`
- Frozen registry SHA-256:
  `2c447b5eee07b2f2930fc8649860652b36d4902dafadfa83e3f5d7aa041a76db`

The previous job failed before source extraction or inference and yielded zero
scientific outputs. This registration authorizes one Gate 2.1 collection, not
an outcome-dependent rerun.
