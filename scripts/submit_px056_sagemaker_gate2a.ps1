param(
  [string]$Profile = "praxis-build",
  [string]$Region = "us-east-1",
  [string]$Bucket = "praxis-garypagan-272615233626-us-east-1",
  [string]$RoleArn = "arn:aws:iam::272615233626:role/service-role/AmazonSageMaker-ExecutionRole-20260416T190919",
  [string]$InstanceType = "ml.g5.2xlarge",
  [string]$ImageUri = "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:2.5.1-gpu-py311-cu124-ubuntu22.04-sagemaker",
  [string]$Mode = "pilot",
  [int]$GenerationsPerPrompt = 3,
  [int]$MaxRuntimeSeconds = 28800
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$JobSource = Join-Path $Root "cloud_jobs\px056_model_output_gate_20260721"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$JobName = "px056-gate2a-live-pilot-$Timestamp"
$Prefix = "experiments/model-registry-hallucination/gate2a-live-pilot-20260721"
$SourceKey = "$Prefix/source/$JobName/source.tar.gz"
$SourceUri = "s3://$Bucket/$SourceKey"
$ResultUri = "s3://$Bucket/$Prefix/results/$JobName/"
$OutputUri = "s3://$Bucket/$Prefix/sagemaker-output/"
$TempDir = Join-Path $env:TEMP $JobName
$TarPath = Join-Path $TempDir "source.tar.gz"
$RunCommand = "set -euo pipefail; mkdir -p /opt/ml/code; cp /opt/ml/input/data/code/source.tar.gz /tmp/source.tar.gz; tar -xzf /tmp/source.tar.gz -C /opt/ml/code; cd /opt/ml/code; python -m pip install --no-cache-dir --upgrade pip; python -m pip install --no-cache-dir -r requirements.txt; python run_px056_gate2_model_output.py --generations-per-prompt $GenerationsPerPrompt --max-input-tokens 1400 --max-new-tokens 384 --mode $Mode --outdir /opt/ml/output/data/px056_gate2_model_output --s3-uri $ResultUri"

if (Test-Path $TempDir) {
  Remove-Item -LiteralPath $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

Push-Location $JobSource
try {
  tar -czf $TarPath run_px056_gate2_model_output.py requirements.txt
} finally {
  Pop-Location
}

aws s3 cp $TarPath $SourceUri --profile $Profile --region $Region --no-progress | Out-Null

$Request = @{
  TrainingJobName = $JobName
  RoleArn = $RoleArn
  AlgorithmSpecification = @{
    TrainingImage = $ImageUri
    TrainingInputMode = "File"
    ContainerEntrypoint = @("bash", "-lc")
    ContainerArguments = @($RunCommand)
  }
  InputDataConfig = @(
    @{
      ChannelName = "code"
      DataSource = @{
        S3DataSource = @{
          S3DataType = "S3Prefix"
          S3Uri = $SourceUri
          S3DataDistributionType = "FullyReplicated"
        }
      }
      InputMode = "File"
    }
  )
  OutputDataConfig = @{
    S3OutputPath = $OutputUri
  }
  ResourceConfig = @{
    InstanceType = $InstanceType
    InstanceCount = 1
    VolumeSizeInGB = 200
  }
  StoppingCondition = @{
    MaxRuntimeInSeconds = $MaxRuntimeSeconds
  }
  Environment = @{
    SAGEMAKER_REGION = $Region
    PX056_S3_URI = $ResultUri
    TOKENIZERS_PARALLELISM = "false"
  }
  HyperParameters = @{
    mode = $Mode
    "generations-per-prompt" = [string]$GenerationsPerPrompt
    "max-new-tokens" = "384"
    "max-input-tokens" = "1400"
    "s3-uri" = $ResultUri
    outdir = "/opt/ml/output/data/px056_gate2_model_output"
  }
  Tags = @(
    @{ Key = "Project"; Value = "PraxisResearch" },
    @{ Key = "PraxisId"; Value = "PX-056" },
    @{ Key = "Gate"; Value = "Gate2A" }
  )
}

$RequestPath = Join-Path $TempDir "create-training-job.json"
$RequestJson = $Request | ConvertTo-Json -Depth 10
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($RequestPath, $RequestJson, $Utf8NoBom)

aws sagemaker create-training-job --cli-input-json file://$RequestPath --profile $Profile --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "aws sagemaker create-training-job failed with exit code $LASTEXITCODE"
}

[pscustomobject]@{
  job_name = $JobName
  source_uri = $SourceUri
  result_uri = $ResultUri
  output_uri = $OutputUri
  describe_command = "aws sagemaker describe-training-job --training-job-name $JobName --profile $Profile --region $Region"
  logs_command = "aws logs tail /aws/sagemaker/TrainingJobs --log-stream-name-prefix $JobName --follow --profile $Profile --region $Region"
} | ConvertTo-Json -Depth 4
