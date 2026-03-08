# AWS Serverless Job Market Intelligence Pipeline

A **fully serverless, event-driven AWS data pipeline** that ingests 100+ job listings daily, transforms and deduplicates them, extracts ML-ready features, and stores everything in a 3-tier partitioned S3 data lake queryable via Amazon Athena.

---

## Architecture

```
EventBridge (daily cron)
        │
        ▼
┌─────────────────┐   raw JSON    ┌─────────────────────────────────────┐
│  Lambda         │ ──────────►  │  S3 Data Lake                       │
│  (Ingestor)     │               │  raw/year=*/month=*/day=*/          │
│  JSearch + LinkedIn APIs        │  processed/year=*/month=*/day=*/    │
│  via Apify      │   S3 trigger  │  features/year=*/month=*/day=*/     │
└─────────────────┘       │       └─────────────────────────────────────┘
                           │                        │
                  ┌────────▼────────┐               │ (Athena partition projection)
                  │ Lambda          │               ▼
                  │ (Transformer)   │        ┌────────────┐
                  │ Normalise +     │        │   Amazon   │
                  │ Deduplicate     │        │   Athena   │
                  └────────┬────────┘        └────────────┘
                           │ S3 trigger
                  ┌────────▼────────┐
                  │ Lambda          │
                  │ (Feature        │
                  │  Extractor)     │
                  │ Skills + Level  │
                  └─────────────────┘
```

---

## Features

| Feature | Detail |
|---------|--------|
| **Ingestion** | Fetches 100+ job records daily from JSearch + LinkedIn via Apify actors |
| **3-Tier S3 Lake** | `raw/` → `processed/` → `features/` with `year/month/day` partitioning |
| **Deduplication** | SHA-256 fingerprint + 30-day rolling window → 25–30% duplicate reduction |
| **Schema Normalisation** | Unified field names, type casting, salary min/max/avg extraction |
| **Feature Engineering** | Skill tokenisation (20+ skills), experience level, remote/hybrid/onsite |
| **Athena Partition Projection** | No MSCK REPAIR needed; cost-efficient multi-month scans |

---

## Project Structure

```
aws-job-market-pipeline/
├── lambdas/
│   ├── ingestor/           # Fetches raw jobs from APIs → S3 raw/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── transformer/        # Normalises + deduplicates → S3 processed/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── feature_extractor/  # Skill / level / mode extraction → S3 features/
│       ├── handler.py
│       └── requirements.txt
├── athena/
│   └── create_tables.sql   # DDL with partition projection for all 3 tiers
├── infra/
│   └── setup_aws.py        # Bootstrap script – S3 + EventBridge + notifications
├── tests/
│   └── test_pipeline_local.py  # 9 unit tests – runs locally, no AWS needed
└── requirements.txt
```

---

## Quickstart

### 1. Clone & install dependencies
```bash
git clone https://github.com/jeeva-s0604/aws-job-market-pipeline.git
cd aws-job-market-pipeline
pip install -r requirements.txt
```

### 2. Run local tests (no AWS credentials needed)
```bash
python -m pytest tests/test_pipeline_local.py -v
```

### 3. Deploy to AWS

#### Prerequisites
- AWS CLI configured (`aws configure`)
- IAM role with: `s3:*`, `lambda:InvokeFunction`, `events:*`, `athena:*`

#### Bootstrap infrastructure
```bash
python infra/setup_aws.py \
  --bucket  your-job-pipeline-bucket \
  --region  ap-south-1 \
  --ingestor-arn    arn:aws:lambda:ap-south-1:ACCOUNT:function:job-ingestor \
  --transformer-arn arn:aws:lambda:ap-south-1:ACCOUNT:function:job-transformer \
  --extractor-arn   arn:aws:lambda:ap-south-1:ACCOUNT:function:job-feature-extractor
```

#### Deploy Lambdas (example using AWS CLI)
```bash
# Package and deploy each Lambda
for fn in ingestor transformer feature_extractor; do
  cd lambdas/$fn
  pip install -r requirements.txt -t package/
  cp handler.py package/
  cd package && zip -r ../function.zip . && cd ..
  aws lambda create-function \
    --function-name job-$fn \
    --runtime python3.12 \
    --handler handler.lambda_handler \
    --zip-file fileb://function.zip \
    --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
    --environment Variables="{S3_BUCKET_NAME=your-bucket,APIFY_API_TOKEN=your-token}" \
    --timeout 180 \
    --memory-size 256
  cd ../..
done
```

#### Set up Athena tables
```bash
# Run create_tables.sql in the Athena console
# or via AWS CLI (replace <YOUR_BUCKET> first):
aws athena start-query-execution \
  --query-string file://athena/create_tables.sql \
  --result-configuration OutputLocation=s3://your-bucket/athena-results/
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_BUCKET_NAME` | `job-market-pipeline-raw` | Target S3 bucket |
| `APIFY_API_TOKEN` | `""` | Apify API key (omit for mock data) |
| `APIFY_ACTOR_ID` | `bebity~linkedin-jobs-scraper` | Apify actor |
| `SEARCH_TERMS` | `Data Engineer,Junior Data Engineer,ETL Developer` | Comma-separated |
| `LOCATIONS` | `India,Remote` | Comma-separated |
| `MAX_RESULTS` | `100` | Max records per API call |
| `FRESHNESS_DAYS` | `30` | Dedup rolling window |

---

## Sample Athena Queries

```sql
-- Top demanded skills this month
SELECT skill, COUNT(*) AS demand_count
FROM job_market_features
CROSS JOIN UNNEST(skills) AS t(skill)
WHERE year = '2025' AND month = '01'
GROUP BY skill ORDER BY demand_count DESC LIMIT 10;

-- Average salary by experience level
SELECT experience_level, ROUND(AVG(salary_avg), 0) AS avg_salary, COUNT(*) AS jobs
FROM job_market_features
WHERE salary_avg IS NOT NULL
GROUP BY experience_level ORDER BY avg_salary DESC;
```

---

## Tech Stack

`Python 3.12` · `AWS Lambda` · `Amazon S3` · `Amazon EventBridge` · `Amazon Athena` · `Boto3` · `Apify`

---

*Built by Jeeva S — [linkedin.com/in/jeeva-s0604](https://linkedin.com/in/jeeva-s0604)*
