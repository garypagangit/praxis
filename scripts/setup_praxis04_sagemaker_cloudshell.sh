#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-praxis04}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
ROLE_NAME="${ROLE_NAME:-Praxis04SageMakerExecutionRole}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-${PROJECT_NAME}-${ACCOUNT_ID}-${AWS_REGION}}"
PREFIX="${PREFIX:-sagemaker/praxis04}"

echo "Region: ${AWS_REGION}"
echo "Account: ${ACCOUNT_ID}"
echo "Bucket: s3://${BUCKET}"
echo "Role: ${ROLE_NAME}"

if aws s3api head-bucket --bucket "${BUCKET}" >/dev/null 2>&1; then
  echo "Bucket already exists."
else
  if [[ "${AWS_REGION}" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "${BUCKET}" --region "${AWS_REGION}"
  else
    aws s3api create-bucket \
      --bucket "${BUCKET}" \
      --region "${AWS_REGION}" \
      --create-bucket-configuration "LocationConstraint=${AWS_REGION}"
  fi
fi

aws s3api put-bucket-versioning \
  --bucket "${BUCKET}" \
  --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
  --bucket "${BUCKET}" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

TRUST_POLICY="$(mktemp)"
cat > "${TRUST_POLICY}" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON

if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  echo "Role already exists."
else
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "file://${TRUST_POLICY}" >/dev/null
fi
rm -f "${TRUST_POLICY}"

aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess >/dev/null || true

S3_POLICY="$(mktemp)"
cat > "${S3_POLICY}" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cse-cic-ids2018",
        "arn:aws:s3:::cse-cic-ids2018/*"
      ]
    }
  ]
}
JSON

aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name Praxis04SageMakerS3Access \
  --policy-document "file://${S3_POLICY}"
rm -f "${S3_POLICY}"

ROLE_ARN="$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)"

mkdir -p "${HOME}/.praxis04"
cat > "${HOME}/.praxis04/sagemaker.env" <<EOF
export AWS_REGION="${AWS_REGION}"
export PRAXIS04_S3_BUCKET="${BUCKET}"
export PRAXIS04_S3_PREFIX="${PREFIX}"
export SAGEMAKER_ROLE_ARN="${ROLE_ARN}"
EOF

echo
echo "SageMaker bootstrap complete."
echo "Saved environment file: ${HOME}/.praxis04/sagemaker.env"
echo
echo "Paste/run this before submitting jobs:"
echo "  source ${HOME}/.praxis04/sagemaker.env"
echo
echo "Role ARN:"
echo "  ${ROLE_ARN}"
