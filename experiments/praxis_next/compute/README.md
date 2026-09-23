# Compute readiness for PX-080 / PX-081 / PX-082

Checked September 23, 2026. Machine-readable evidence is in [aws_readiness.json](aws_readiness.json).

- The configured AWS profile is `praxis-build`.
- `aws sts get-caller-identity --profile praxis-build` returned an expired or invalid SSO session.
- A bounded `aws sso login --profile praxis-build --no-browser --use-device-code` attempt produced device-authorization instructions but did not complete. The process was stopped after 15 seconds. A preceding bounded attempt also did not complete.
- No AWS inventory was verified, no worker was launched, and no AWS model fit ran in this readiness task. Existing resources must not be described as stopped or absent based on these checks.
- No login code, authorization URL, credential, or token was written into repository artifacts.

The user requested continuation without questions. Local fitting and data qualification therefore continue independently. AWS becomes usable after its normal SSO authorization succeeds; the agent cannot replace the user's required identity verification. The [Chrome skill](C:/Users/garyp/.codex/plugins/cache/openai-bundled/chrome/26.623.101652/skills/control-chrome/SKILL.md) says: "Do not switch to Chrome solely because a preferred connector, API, or CLI has missing or expired authentication." Its explicit Chrome-fallback approval requirement was not fulfilled by a separate Chrome instruction, so no browser authentication or MFA bypass was attempted.

For a later authenticated worker, require a verified account/region, an explicit job payload and resource ceiling, durable output retrieval, and a stop-on-exit mechanism before launch. GPU use should be driven by the actual neural-model workload; the present small tree pilots do not gain automatically from a GPU.
