"""
infra/setup_aws.py
------------------
One-time bootstrap script that creates:
  1. S3 bucket with versioning + lifecycle rules
  2. EventBridge rule (daily 06:00 UTC → ingestor Lambda)
  3. S3 notification → transformer Lambda (raw/ prefix)
  4. S3 notification → feature_extractor Lambda (processed/ prefix)

Usage:
    python infra/setup_aws.py --bucket my-job-pipeline --region ap-south-1

Requirements:
    pip install boto3
    AWS credentials with appropriate IAM permissions
"""

import argparse
import json
import boto3
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def create_s3_bucket(s3, bucket: str, region: str):
    log.info("Creating S3 bucket: %s  (region=%s)", bucket, region)
    kwargs = {"Bucket": bucket}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    try:
        s3.create_bucket(**kwargs)
    except s3.exceptions.BucketAlreadyOwnedByYou:
        log.info("Bucket already exists – skipping creation.")

    # Enable versioning
    s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )

    # Lifecycle: expire raw/ objects after 90 days; processed/ after 365 days
    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-raw-90d",
                    "Filter": {"Prefix": "raw/"},
                    "Status": "Enabled",
                    "Expiration": {"Days": 90},
                },
                {
                    "ID": "expire-processed-365d",
                    "Filter": {"Prefix": "processed/"},
                    "Status": "Enabled",
                    "Expiration": {"Days": 365},
                },
                {
                    "ID": "expire-features-365d",
                    "Filter": {"Prefix": "features/"},
                    "Status": "Enabled",
                    "Expiration": {"Days": 365},
                },
            ]
        },
    )
    log.info("S3 bucket configured with versioning + lifecycle rules.")


def create_eventbridge_rule(events, lambda_arn: str, region: str):
    rule_name = "job-market-daily-ingest"
    log.info("Creating EventBridge rule: %s", rule_name)

    resp = events.put_rule(
        Name               = rule_name,
        ScheduleExpression = "cron(0 6 * * ? *)",   # 06:00 UTC daily
        State              = "ENABLED",
        Description        = "Trigger job market ingestor Lambda every day at 06:00 UTC",
    )
    rule_arn = resp["RuleArn"]
    log.info("Rule ARN: %s", rule_arn)

    events.put_targets(
        Rule    = rule_name,
        Targets = [{"Id": "IngestorLambda", "Arn": lambda_arn}],
    )
    log.info("Target attached to rule.")
    return rule_arn


def add_s3_notification(s3, bucket: str, transformer_arn: str, extractor_arn: str):
    """Configure S3 event notifications for both Lambda functions."""
    log.info("Configuring S3 event notifications…")
    s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": transformer_arn,
                    "Events":            ["s3:ObjectCreated:*"],
                    "Filter":            {"Key": {"FilterRules": [{"Name": "prefix", "Value": "raw/"}]}},
                },
                {
                    "LambdaFunctionArn": extractor_arn,
                    "Events":            ["s3:ObjectCreated:*"],
                    "Filter":            {"Key": {"FilterRules": [{"Name": "prefix", "Value": "processed/"}]}},
                },
            ]
        },
    )
    log.info("S3 notifications configured.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket",          required=True, help="S3 bucket name")
    parser.add_argument("--region",          default="ap-south-1")
    parser.add_argument("--ingestor-arn",    default="", help="ARN of ingestor Lambda")
    parser.add_argument("--transformer-arn", default="", help="ARN of transformer Lambda")
    parser.add_argument("--extractor-arn",   default="", help="ARN of feature_extractor Lambda")
    args = parser.parse_args()

    session  = boto3.Session(region_name=args.region)
    s3       = session.client("s3")
    events   = session.client("events")

    create_s3_bucket(s3, args.bucket, args.region)

    if args.ingestor_arn:
        create_eventbridge_rule(events, args.ingestor_arn, args.region)
    else:
        log.warning("--ingestor-arn not provided – skipping EventBridge rule.")

    if args.transformer_arn and args.extractor_arn:
        add_s3_notification(s3, args.bucket, args.transformer_arn, args.extractor_arn)
    else:
        log.warning("Lambda ARNs not provided – skipping S3 notifications.")

    log.info("✅  Infrastructure setup complete.")


if __name__ == "__main__":
    main()
