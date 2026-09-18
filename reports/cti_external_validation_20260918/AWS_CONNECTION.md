# AWS connection

Connected and verified September 18, 2026 through the existing AWS IAM Identity Center sign-in.

- CLI profile: `praxis-build`
- Region: `us-east-1`
- Account identity: verified against the designated Praxis account.
- Existing experiment host: verified `g5.xlarge`, STOPPED before this attempt.
- Credentials: temporary SSO session managed by AWS CLI. No access keys or tokens copied into this repository.

The user authorized setting up AWS and using it for the continuing CTI experiment. The session was authenticated through the existing Chrome AWS session and verified with AWS STS. Private account/host details and the verification timestamp are in `C:/w/cti_external_private_20260918/AWS_CONNECTION_VERIFIED.json`.

## Use and renewal

Use `--profile praxis-build --region us-east-1` on AWS CLI commands. Check connectivity with:

```powershell
aws sts get-caller-identity --profile praxis-build
```

When the temporary session expires, renew it with:

```powershell
aws sso login --profile praxis-build --use-device-code --no-browser
```

Open the newly issued AWS link, verify its device code and complete the account's sign-in/consent. A fresh password or MFA request must be completed by the account holder if required; no permanent credentials are needed for this workflow.

## Experiment use

The external CTI run uses the existing GPU host with a one-hour ceiling, a separate automatic stop timer and a $10 total reserve. The reserved estimate includes at most $1.006 for one hour of compute plus a $5 incidental allowance; this is an estimate using the recorded September 16 rate, not an invoice. The runtime manifest and immutable Git commit are checked before launch. Results and the final STOPPED observation are recorded in the private execution receipt and summarized in the experiment report.
