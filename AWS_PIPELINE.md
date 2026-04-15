# Praxis AWS Pipeline

This is the high-performance, low-friction workflow for Praxis. The goal is to stop bouncing between local, GitHub, Colab, and Drive.

## Architecture

- Code lives in GitHub: `garypagangit/praxis`
- The Unraveled dataset lives in Amazon S3
- A persistent EC2 GPU instance does the training
- A large attached EBS volume stores the repo, caches, datasets, and outputs
- You connect to the instance with SSH plus VS Code Remote SSH or an SSH tunnel to Jupyter

## Easiest Connection Modes

### Option 1: Session Manager

This is the easiest connection path if your local machine is awkward about SSH tooling.

- no inbound SSH needed
- no local SSH key management required
- browser-based shell from the AWS console

Attach an instance role with `AmazonSSMManagedInstanceCore`, then connect through the EC2 console or Systems Manager.

### Option 2: EC2 Instance Connect

This is the easiest direct SSH-style connection from the AWS console for Ubuntu.

- simple browser-based connect flow
- good for quick one-off admin work

### Option 3: SSH + Jupyter tunnel

This is the best daily workflow after the instance is stable.

- run Jupyter on the EC2 box
- forward one local port
- keep the notebook server on the instance, not on your laptop

## Recommended AWS Build

- Default region for a persistent workflow: `us-east-1`
- First-choice persistent instance: `p5en.48xlarge`
- Fallback persistent instance: `p5e.48xlarge`
- Highest-peak-performance option: `p6-b200.48xlarge` in `us-west-2` through EC2 Capacity Blocks for ML
- AMI: latest `AWS Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)`
- Root disk: default is fine
- Data disk: `gp3`, `4096 GiB`, `16000 IOPS`, `1000 MiB/s`

## Required AWS Resources

1. One S3 bucket for datasets and exported run artifacts
2. One EC2 key pair, unless you plan to use Session Manager only
3. One IAM role for the EC2 instance with:
   - `AmazonSSMManagedInstanceCore`
   - read and write access to your Praxis S3 bucket
4. One security group:
   - allow inbound `22` from your IP only
   - do not open `8888` unless you explicitly want browser Jupyter access

## Local To Cloud Flow

1. Configure the AWS CLI locally.
2. Create your S3 bucket.
3. Upload the Unraveled dataset once from this machine.
4. Launch the EC2 instance.
5. Attach the IAM role and large EBS data volume.
6. SSH into the instance and run `scripts/bootstrap_aws_gpu_ubuntu.sh`.
7. Sync the dataset down from S3 to `/mnt/praxis/data/unraveled/network-flows`.
8. Run Praxis from the AWS-specific configs in `configs/`.

## Suggested Names

- AWS CLI profile: `praxis-build`
- Bucket: `praxis-garypagangit-us-east-1`
- EC2 hostname tag: `praxis-trainer`
- Mount point: `/mnt/praxis`

## Local AWS CLI Setup

Preferred if your org supports it:

```powershell
aws configure sso --profile praxis-build
aws sts get-caller-identity --profile praxis-build
```

If your account uses access keys instead:

```powershell
aws configure --profile praxis-build
aws sts get-caller-identity --profile praxis-build
```

## If Windows Blocks AWS CLI Installation

Some locked-down Windows machines block the AWS CLI MSI installer with a system-policy error.

If that happens, use the AWS web console for the first control-plane steps:

1. create the S3 bucket in the console
2. launch the EC2 instance in the console
3. attach the IAM role in the console
4. either upload the dataset through the S3 web UI or copy it directly to the EC2 instance with `scp`

Once the EC2 instance is live, the Linux side of this repo still works the same.

## Create The S3 Bucket

```powershell
aws s3 mb s3://praxis-garypagangit-us-east-1 --region us-east-1 --profile praxis-build
```

## Upload The Unraveled Dataset From Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync_unraveled_to_s3.ps1 `
  -BucketName praxis-garypagangit-us-east-1 `
  -Profile praxis-build
```

That uploads to:

```text
s3://praxis-garypagangit-us-east-1/datasets/unraveled/network-flows/
```

## Bootstrap The EC2 Instance

After SSH login:

```bash
chmod +x scripts/bootstrap_aws_gpu_ubuntu.sh
./scripts/bootstrap_aws_gpu_ubuntu.sh
```

If you are connecting through Session Manager instead of SSH, the same commands work in the browser shell.

## Pull The Dataset Onto The Instance

On the EC2 instance:

```bash
chmod +x scripts/sync_unraveled_from_s3.sh
AWS_PROFILE=default S3_BUCKET=praxis-garypagangit-us-east-1 ./scripts/sync_unraveled_from_s3.sh
```

If you attach an instance role with S3 access, you usually do not need to set `AWS_PROFILE`.

## Run Praxis On AWS

```bash
cd /mnt/praxis/repo
source .venv/bin/activate
python -m praxis.train --config configs/praxisv03-unraveled-aws-mamba-proper.json
```

Follow-up runs:

```bash
python -m praxis.train --config configs/praxisv03-unraveled-aws-graph-chunk128.json
python -m praxis.train --config configs/praxisv03-unraveled-aws-graph-de-weighted.json
```

## Start Jupyter On The Instance

On the EC2 instance:

```bash
chmod +x scripts/start_jupyter_aws.sh
./scripts/start_jupyter_aws.sh
```

If `tmux` is available, this starts JupyterLab in a background session named `praxis-jupyter`.

## Open A Tunnel From Windows

From this Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_aws_jupyter_tunnel.ps1 `
  -Host YOUR-EC2-DNS-NAME `
  -User ubuntu `
  -KeyPath C:\path\to\your-key.pem
```

Then open:

```text
http://127.0.0.1:8888
```

Use the Jupyter token printed in the EC2 shell or visible in the `tmux` output.

## Working Style

- Edit locally or via VS Code Remote SSH
- Commit and push to GitHub
- On EC2, `git pull`
- Train on the EC2 box
- Sync outputs back to S3 if needed

## Why This Pipeline Is Better

- No Colab runtime resets
- No Google Drive dependency
- No repeated package installs
- No notebook state drift between sessions
- One persistent GPU box with one persistent dataset location
