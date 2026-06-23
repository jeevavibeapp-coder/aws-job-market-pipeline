"""
infra/monitoring.py
-------------------
Provisions observability for the pipeline:
  1. SNS topic for alerts (subscribe your email after creation)
  2. CloudWatch alarms per Lambda  (Errors, Throttles, Duration p99)
  3. A CloudWatch alarm on the custom data-quality metric (dq_pass_rate)
  4. A CloudWatch dashboard summarising the whole pipeline

Usage:
    python infra/monitoring.py --region ap-south-1 --email you@example.com
"""

import argparse
import json
import logging

import boto3

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

FUNCTIONS = ["job-ingestor", "job-transformer", "job-feature-extractor", "job-loader", "job-insights"]
NAMESPACE = "JobMarketPipeline"


def ensure_topic(sns, name: str, email: str | None) -> str:
    arn = sns.create_topic(Name=name)["TopicArn"]
    log.info("SNS topic ready: %s", arn)
    if email:
        sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=email)
        log.info("Subscription request sent to %s (confirm via email).", email)
    return arn


def create_lambda_alarms(cw, fn: str, topic_arn: str):
    common = {"AlarmActions": [topic_arn], "TreatMissingData": "notBreaching"}

    cw.put_metric_alarm(
        AlarmName=f"{fn}-errors",
        Namespace="AWS/Lambda",
        MetricName="Errors",
        Dimensions=[{"Name": "FunctionName", "Value": fn}],
        Statistic="Sum",
        Period=300,
        EvaluationPeriods=1,
        Threshold=1,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        AlarmDescription=f"{fn} produced at least one error in 5 minutes.",
        **common,
    )
    cw.put_metric_alarm(
        AlarmName=f"{fn}-throttles",
        Namespace="AWS/Lambda",
        MetricName="Throttles",
        Dimensions=[{"Name": "FunctionName", "Value": fn}],
        Statistic="Sum",
        Period=300,
        EvaluationPeriods=1,
        Threshold=1,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        AlarmDescription=f"{fn} is being throttled.",
        **common,
    )
    cw.put_metric_alarm(
        AlarmName=f"{fn}-duration-p99",
        Namespace="AWS/Lambda",
        MetricName="Duration",
        Dimensions=[{"Name": "FunctionName", "Value": fn}],
        ExtendedStatistic="p99",
        Period=300,
        EvaluationPeriods=3,
        Threshold=170000,
        ComparisonOperator="GreaterThanThreshold",  # 170s, near 180s timeout
        AlarmDescription=f"{fn} p99 duration approaching timeout.",
        **common,
    )
    log.info("Alarms created for %s", fn)


def create_dq_alarm(cw, topic_arn: str):
    cw.put_metric_alarm(
        AlarmName="pipeline-data-quality-low",
        Namespace=NAMESPACE,
        MetricName="dq_pass_rate",
        Statistic="Average",
        Period=3600,
        EvaluationPeriods=1,
        Threshold=0.8,
        ComparisonOperator="LessThanThreshold",
        AlarmActions=[topic_arn],
        TreatMissingData="notBreaching",
        AlarmDescription="Batch data-quality pass rate fell below 80%.",
    )
    log.info("Data-quality alarm created.")


def create_dashboard(cw, region: str):
    def lambda_widget(title, metric):
        return {
            "type": "metric",
            "width": 12,
            "height": 6,
            "properties": {
                "title": title,
                "region": region,
                "stat": "Sum",
                "period": 300,
                "metrics": [["AWS/Lambda", metric, "FunctionName", fn] for fn in FUNCTIONS],
            },
        }

    body = {
        "widgets": [
            lambda_widget("Lambda Invocations", "Invocations"),
            lambda_widget("Lambda Errors", "Errors"),
            {
                "type": "metric",
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Rows Loaded to PostgreSQL",
                    "region": region,
                    "stat": "Sum",
                    "period": 86400,
                    "metrics": [[NAMESPACE, "rows_loaded"]],
                },
            },
            {
                "type": "metric",
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Data Quality Pass Rate",
                    "region": region,
                    "stat": "Average",
                    "period": 3600,
                    "yAxis": {"left": {"min": 0, "max": 1}},
                    "metrics": [[NAMESPACE, "dq_pass_rate"]],
                },
            },
        ]
    }
    cw.put_dashboard(DashboardName="JobMarketPipeline", DashboardBody=json.dumps(body))
    log.info("Dashboard 'JobMarketPipeline' created.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="ap-south-1")
    p.add_argument("--email", default="", help="Email to subscribe to alerts")
    args = p.parse_args()

    session = boto3.Session(region_name=args.region)
    sns = session.client("sns")
    cw = session.client("cloudwatch")

    topic_arn = ensure_topic(sns, "job-market-alerts", args.email or None)
    for fn in FUNCTIONS:
        create_lambda_alarms(cw, fn, topic_arn)
    create_dq_alarm(cw, topic_arn)
    create_dashboard(cw, args.region)

    log.info("✅  Monitoring setup complete. Alert topic: %s", topic_arn)


if __name__ == "__main__":
    main()
